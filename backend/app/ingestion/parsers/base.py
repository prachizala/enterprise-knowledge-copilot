"""Base parser interfaces and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class ParsedPage:
    """Represents a discrete page or logical section within a document."""
    content: str
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Represents the complete parsed extraction of an enterprise document."""
    filename: str
    file_type: str
    pages: List[ParsedPage]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Concatenate all page contents."""
        return "\n\n".join(p.content for p in self.pages if p.content.strip())


class BaseParser(ABC):
    """Abstract base parser for enterprise document file formats."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a local file and return structured document pages."""
        pass
