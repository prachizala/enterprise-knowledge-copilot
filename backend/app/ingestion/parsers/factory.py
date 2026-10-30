"""Parser factory resolving file extensions to specialized document parsers."""

from pathlib import Path
from typing import Dict, Type

from app.ingestion.parsers.base import BaseParser
from app.ingestion.parsers.pdf_parser import PDFParser
from app.ingestion.parsers.docx_parser import DocxParser
from app.ingestion.parsers.text_parser import TextParser
from app.ingestion.parsers.csv_parser import CSVParser


class ParserFactory:
    """Factory to dispatch documents to corresponding format parsers."""

    _PARSERS: Dict[str, Type[BaseParser]] = {
        ".pdf": PDFParser,
        ".docx": DocxParser,
        ".txt": TextParser,
        ".md": TextParser,
        ".markdown": TextParser,
        ".csv": CSVParser,
        ".json": TextParser,
    }

    @classmethod
    def get_parser(cls, file_path: Path) -> BaseParser:
        """Resolve and instantiate parser for the given file extension."""
        ext = file_path.suffix.lower()
        parser_cls = cls._PARSERS.get(ext)
        if not parser_cls:
            supported = ", ".join(cls._PARSERS.keys())
            raise ValueError(
                f"Unsupported file format '{ext}'. Supported formats: {supported}"
            )
        return parser_cls()
