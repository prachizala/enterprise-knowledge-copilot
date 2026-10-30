"""Document Ingestion and Processing Pipeline."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.models.document import DocumentModel, DocumentChunkModel
from app.ingestion.parsers.factory import ParserFactory
from app.ingestion.chunker import TextChunker, Chunk

logger = logging.getLogger(__name__)

# Base Data Directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


class IngestionPipeline:
    """Orchestrates parsing, chunking, and persistence of enterprise documents."""

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
    ):
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    @staticmethod
    def calculate_sha256(content_bytes: bytes) -> str:
        """Compute SHA256 hex digest of file bytes."""
        hasher = hashlib.sha256()
        hasher.update(content_bytes)
        return hasher.hexdigest()

    def process_file_bytes(
        self,
        db: Session,
        filename: str,
        content_bytes: bytes,
        department: str = "Engineering",
        owner: str = "Alex Morgan",
    ) -> DocumentModel:
        """Ingest document from byte stream, parse, chunk, and commit to database."""
        doc_id = str(uuid.uuid4())
        file_hash = self.calculate_sha256(content_bytes)
        file_ext = Path(filename).suffix.lower()

        # Destination file path in data/uploads/
        safe_filename = f"{doc_id[:8]}_{filename}"
        saved_path = UPLOADS_DIR / safe_filename
        saved_path.write_bytes(content_bytes)

        # Initial Document Record
        doc = DocumentModel(
            id=doc_id,
            filename=filename,
            file_path=str(saved_path),
            file_type=file_ext.lstrip(".").upper() or "UNKNOWN",
            file_size=len(content_bytes),
            file_hash=file_hash,
            department=department,
            owner=owner,
            status="PROCESSING",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        try:
            # 1. Parse Document using appropriate parser
            parser = ParserFactory.get_parser(saved_path)
            parsed_doc = parser.parse(saved_path)

            # 2. Chunk Document into semantic passages
            chunks = self.chunker.chunk_document(parsed_doc)

            # 3. Persist Chunks in Database
            chunk_models: List[DocumentChunkModel] = []
            for ch in chunks:
                chunk_model = DocumentChunkModel(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    chunk_index=ch.index,
                    content=ch.content,
                    char_count=ch.char_count,
                    token_count=ch.token_count,
                    page_number=ch.page_number,
                    section_header=ch.section_header,
                    metadata_json=json.dumps(ch.metadata),
                )
                chunk_models.append(chunk_model)

            db.add_all(chunk_models)

            # 4. Save processed JSON artifact to data/processed/
            processed_file = PROCESSED_DIR / f"{doc_id}.json"
            processed_data = {
                "id": doc_id,
                "filename": filename,
                "file_type": doc.file_type,
                "department": department,
                "owner": owner,
                "total_chunks": len(chunks),
                "chunks": [
                    {
                        "index": ch.index,
                        "content": ch.content,
                        "char_count": ch.char_count,
                        "token_count": ch.token_count,
                        "page_number": ch.page_number,
                        "section_header": ch.section_header,
                        "metadata": ch.metadata,
                    }
                    for ch in chunks
                ],
            }
            processed_file.write_text(json.dumps(processed_data, indent=2), encoding="utf-8")

            # 5. Update Document Status to PROCESSED
            doc.status = "PROCESSED"
            doc.total_chunks = len(chunks)
            doc.error_message = None
            db.commit()
            db.refresh(doc)
            logger.info(f"Successfully processed document {filename} ({len(chunks)} chunks).")
            return doc

        except Exception as e:
            db.rollback()
            logger.error(f"Error processing document {filename}: {e}", exc_info=True)
            doc.status = "FAILED"
            doc.error_message = str(e)
            db.commit()
            db.refresh(doc)
            return doc

    def delete_document(self, db: Session, doc_id: str) -> bool:
        """Delete document record, chunks, and corresponding disk files."""
        doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        if not doc:
            return False

        # Remove local upload file if exists
        try:
            if doc.file_path and Path(doc.file_path).exists():
                Path(doc.file_path).unlink(missing_ok=True)
            processed_file = PROCESSED_DIR / f"{doc_id}.json"
            if processed_file.exists():
                processed_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Could not delete physical files for {doc_id}: {e}")

        db.delete(doc)
        db.commit()
        return True
