"""Base classes, data models, and exceptions for document text extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


class ExtractionError(Exception):
    """Base exception for document extraction failures."""
    pass


class UnsupportedFileTypeError(ExtractionError):
    """Raised when file type or extension is unsupported."""
    pass


class EmptyContentError(ExtractionError):
    """Raised when a document has zero extractable text (e.g. scanned image or empty file)."""
    pass


class CorruptDocumentError(ExtractionError):
    """Raised when a document is damaged or malformed."""
    pass


@dataclass
class ExtractedContent:
    """Standardized representation of text and structural metrics extracted from a document."""
    text: str
    page_count: Optional[int] = None
    character_count: int = field(init=False)
    word_count: int = field(init=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.character_count = len(self.text)
        self.word_count = len(self.text.split()) if self.text else 0


class BaseExtractor(ABC):
    """Abstract interface for all document type extractors."""

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractedContent:
        """Extract text content and page/structural metrics from file.

        Args:
            file_path: Absolute path to the document file.

        Returns:
            ExtractedContent containing structured text and counts.

        Raises:
            EmptyContentError: When file yields no extractable text.
            CorruptDocumentError: When parsing fails due to bad format.
            ExtractionError: For unexpected extraction failures.
        """
        pass
