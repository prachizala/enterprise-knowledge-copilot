from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.service import EmbeddingService
from app.extraction.entities.service import EntityExtractionService
from app.extraction.relationships.service import RelationshipExtractionService
from app.graph.sync_service import graph_sync_service
from app.models.document import Document
from app.models.job import ProcessingJob
from app.services.document_service import document_service

logger = logging.getLogger(__name__)


class DocumentIngestionOrchestrator:
    """
    End-to-end ingestion pipeline orchestrator:
    1. Text Extraction
    2. Structure-Aware Chunking
    3. Dense Vector Embeddings Generation
    4. Named Entity Extraction & Normalization
    5. Typed Relationship Extraction
    6. Neo4j Knowledge Graph Synchronization
    """

    async def run_pipeline(
        self,
        db: AsyncSession,
        document_id: str,
        job_id: Optional[str] = None,
        force_retry: bool = False,
    ) -> ProcessingJob:
        # 1. Resolve or create Job record
        job: Optional[ProcessingJob] = None
        if job_id:
            res = await db.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )
            job = res.scalars().first()

        if not job:
            job = ProcessingJob(
                id=str(uuid4()),
                document_id=document_id,
                job_type="full_pipeline",
                status="running",
                current_step="extract",
                progress_pct=10,
                details={},
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
        else:
            job.status = "running"
            job.current_step = "extract"
            job.progress_pct = 10
            job.error_message = None
            await db.commit()

        start_time = time.perf_counter()
        metrics: Dict[str, Any] = {}

        try:
            # Verify document exists
            doc_res = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = doc_res.scalars().first()
            if not doc:
                raise ValueError(f"Document {document_id} not found in database.")

            # STEP 1: Text Extraction (15%)
            logger.info(f"Ingestion [{document_id}] Step 1/6: Extracting text...")
            job.current_step = "extract"
            job.progress_pct = 15
            await db.commit()

            doc = await document_service.process_document(db=db, document_id=document_id)
            if doc.status == "failed" or doc.extraction_status == "failed":
                raise RuntimeError(f"Text extraction failed: {doc.error_message}")
            metrics["extraction"] = "success"

            # STEP 2: Structure-Aware Chunking (35%)
            logger.info(f"Ingestion [{document_id}] Step 2/6: Chunking document...")
            job.current_step = "chunk"
            job.progress_pct = 35
            await db.commit()

            # Ensure chunks are generated if not already chunked or if force_retry
            chunks, total_chunks = await document_service.get_document_chunks(
                db=db, document_id=document_id, limit=1
            )
            if total_chunks == 0 or force_retry:
                # Trigger chunking via service
                await document_service.chunk_document(db=db, document_id=document_id)
                chunks, total_chunks = await document_service.get_document_chunks(
                    db=db, document_id=document_id, limit=1
                )
            metrics["chunks_count"] = total_chunks

            # STEP 3: Vector Embeddings (55%)
            logger.info(f"Ingestion [{document_id}] Step 3/6: Generating embeddings...")
            job.current_step = "embed"
            job.progress_pct = 55
            await db.commit()

            emb_res = await EmbeddingService.generate_document_embeddings(
                db=db, document_id=document_id, force=force_retry
            )
            metrics["embedded_chunks"] = emb_res.embedded_chunks

            # STEP 4: Entity Extraction & Normalization (75%)
            logger.info(f"Ingestion [{document_id}] Step 4/6: Extracting entities...")
            job.current_step = "entities"
            job.progress_pct = 75
            await db.commit()

            entity_stats = await EntityExtractionService.extract_document_entities(
                db=db, document_id=document_id, force=force_retry
            )
            metrics["entities_found"] = entity_stats.entities_found
            metrics["unique_entities"] = entity_stats.unique_entities

            # STEP 5: Relationship Extraction (90%)
            logger.info(f"Ingestion [{document_id}] Step 5/6: Extracting relationships...")
            job.current_step = "relationships"
            job.progress_pct = 90
            await db.commit()

            rel_stats = await RelationshipExtractionService.extract_document_relationships(
                db=db, document_id=document_id, force=force_retry
            )
            metrics["relationships_created"] = rel_stats.relationships_created

            # STEP 6: Neo4j Knowledge Graph Sync (100%)
            logger.info(f"Ingestion [{document_id}] Step 6/6: Syncing with Neo4j Knowledge Graph...")
            job.current_step = "graph_sync"
            job.progress_pct = 95
            await db.commit()

            try:
                sync_res = await graph_sync_service.sync(
                    db=db, document_id=document_id, force=force_retry
                )
                metrics["graph_entities_synced"] = sync_res.entities_synced
                metrics["graph_relationships_synced"] = sync_res.relationships_synced
                doc.graph_sync_status = "synced"
            except Exception as graph_err:
                logger.warning(f"Neo4j sync warning (continuing): {graph_err}")
                metrics["graph_sync_warning"] = str(graph_err)
                doc.graph_sync_status = "partial_error"

            total_elapsed_ms = (time.perf_counter() - start_time) * 1000
            metrics["total_duration_ms"] = round(total_elapsed_ms, 2)

            # Mark completed
            job.status = "completed"
            job.current_step = "completed"
            job.progress_pct = 100
            job.details = metrics
            job.completed_at = datetime.now(timezone.utc)
            doc.status = "processed"

            await db.commit()
            await db.refresh(job)
            logger.info(f"Ingestion [{document_id}] completed successfully in {total_elapsed_ms:.1f}ms.")
            return job

        except Exception as e:
            logger.error(f"Ingestion pipeline failed for document {document_id}: {e}", exc_info=True)
            total_elapsed_ms = (time.perf_counter() - start_time) * 1000
            metrics["total_duration_ms"] = round(total_elapsed_ms, 2)

            job.status = "failed"
            job.error_message = str(e)
            job.details = metrics
            await db.commit()
            await db.refresh(job)
            return job


ingestion_orchestrator = DocumentIngestionOrchestrator()
