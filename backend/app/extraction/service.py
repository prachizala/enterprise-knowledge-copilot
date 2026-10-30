"""Unified Extraction Service routing files to format-specific extractors."""

import logging
from pathlib import Path
from typing import Dict, Type

from app.extraction.base import (
    BaseExtractor,
    ExtractedContent,
    UnsupportedFileTypeError,
)
from app.extraction.csv import CSVExtractor
from app.extraction.docx import DocxExtractor
from app.extraction.pdf import PDFExtractor
from app.extraction.txt import TxtExtractor

logger = logging.getLogger(__name__)


class ExtractionService:
    """Manages format extractors and executes extraction pipelines."""

    def __init__(self) -> None:
        self._extractors: Dict[str, BaseExtractor] = {
            "pdf": PDFExtractor(),
            "docx": DocxExtractor(),
            "txt": TxtExtractor(),
            "md": TxtExtractor(),
            "csv": CSVExtractor(),
        }

    def register_extractor(self, extension: str, extractor: BaseExtractor) -> None:
        """Register or override an extractor for a given extension."""
        self._extractors[extension.lower().lstrip(".")] = extractor

    def extract(self, file_path: Path, file_type: str) -> ExtractedContent:
        """Extract text and metadata from the specified document.

        Args:
            file_path: Path to the target document.
            file_type: Extension or type string (e.g. 'pdf', 'docx', 'txt', 'csv').

        Returns:
            ExtractedContent containing structured text, character/word counts, and metrics.

        Raises:
            UnsupportedFileTypeError: If file_type is not registered.
            EmptyContentError: If document produces zero text.
            CorruptDocumentError: If document is malformed.
        """
        normalized_type = file_type.lower().lstrip(".")
        extractor = self._extractors.get(normalized_type)

        if not extractor:
            logger.error(f"Unsupported file type '{normalized_type}' for extraction: {file_path}")
            raise UnsupportedFileTypeError(
                f"Unsupported document format '{normalized_type}'. "
                f"Supported types: {', '.join(sorted(self._extractors.keys()))}"
            )

        logger.info(f"Extracting content from '{file_path.name}' using {extractor.__class__.__name__}")
        return extractor.extract(file_path)


extraction_service = ExtractionService()
