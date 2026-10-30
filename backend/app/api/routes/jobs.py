from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.ingestion.orchestrator import ingestion_orchestrator
from app.models.document import Document
from app.models.job import ProcessingJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Ingestion Jobs"])


class JobResponse(BaseModel):
    id: str
    document_id: str
    job_type: str
    status: str
    current_step: str
    progress_pct: int
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


@router.post("/documents/{document_id}/pipeline", response_model=JobResponse)
async def trigger_full_pipeline(
    document_id: str,
    force_retry: bool = Query(False, description="Force reprocessing of all steps"),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the complete 6-stage ingestion pipeline for a document:
    Extract -> Chunk -> Embed -> Entities -> Relationships -> Neo4j Sync.
    """
    doc_res = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_res.scalars().first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    job = await ingestion_orchestrator.run_pipeline(
        db=db,
        document_id=document_id,
        force_retry=force_retry,
    )
    return job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the real-time status, step progression, and details of a background job."""
    res = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job = res.scalars().first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job


@router.get("/documents/{document_id}/latest", response_model=Optional[JobResponse])
async def get_latest_document_job(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the latest processing job status for a given document."""
    res = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(desc(ProcessingJob.created_at))
        .limit(1)
    )
    job = res.scalars().first()
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed or stalled processing job."""
    res = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job = res.scalars().first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    retried_job = await ingestion_orchestrator.run_pipeline(
        db=db,
        document_id=job.document_id,
        job_id=job.id,
        force_retry=True,
    )
    return retried_job
