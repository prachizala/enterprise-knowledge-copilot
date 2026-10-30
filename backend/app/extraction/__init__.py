"""Document Text Extraction Package."""

from app.extraction.base import (
    BaseExtractor,
    CorruptDocumentError,
    EmptyContentError,
    ExtractionError,
    ExtractedContent,
    UnsupportedFileTypeError,
)
from app.extraction.csv import CSVExtractor
from app.extraction.docx import DocxExtractor
from app.extraction.pdf import PDFExtractor
from app.extraction.service import ExtractionService, extraction_service
from app.extraction.txt import TxtExtractor

__all__ = [
    "BaseExtractor",
    "ExtractedContent",
    "ExtractionError",
    "UnsupportedFileTypeError",
    "EmptyContentError",
    "CorruptDocumentError",
    "PDFExtractor",
    "DocxExtractor",
    "TxtExtractor",
    "CSVExtractor",
    "ExtractionService",
    "extraction_service",
]
