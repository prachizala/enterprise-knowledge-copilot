"""PDF Document Parser using pypdf."""

from pathlib import Path
from typing import List
from pypdf import PdfReader

from app.ingestion.parsers.base import BaseParser, ParsedDocument, ParsedPage


class PDFParser(BaseParser):
    """Parses PDF documents into page-level text units with page numbers."""

    def parse(self, file_path: Path) -> ParsedDocument:
        reader = PdfReader(str(file_path))
        pages: List[ParsedPage] = []

        total_pages = len(reader.pages)
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages.append(
                    ParsedPage(
                        content=text,
                        page_number=idx,
                        metadata={"total_pages": total_pages},
                    )
                )

        metadata = {
            "total_pages": total_pages,
            "extracted_pages": len(pages),
        }

        # Extract PDF metadata if available
        if reader.metadata:
            if reader.metadata.title:
                metadata["title"] = reader.metadata.title
            if reader.metadata.author:
                metadata["author"] = reader.metadata.author

        return ParsedDocument(
            filename=file_path.name,
            file_type="PDF",
            pages=pages,
            metadata=metadata,
        )
