"""DOCX Document Parser using python-docx."""

from pathlib import Path
from typing import List
import docx

from app.ingestion.parsers.base import BaseParser, ParsedDocument, ParsedPage


class DocxParser(BaseParser):
    """Parses Microsoft Word (.docx) files into paragraphs and sections."""

    def parse(self, file_path: Path) -> ParsedDocument:
        doc = docx.Document(str(file_path))
        pages: List[ParsedPage] = []
        current_section = "General"
        current_paras: List[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            # Check if this paragraph represents a heading
            if p.style and p.style.name.startswith("Heading"):
                if current_paras:
                    pages.append(
                        ParsedPage(
                            content="\n".join(current_paras),
                            section_header=current_section,
                        )
                    )
                    current_paras = []
                current_section = text
            else:
                current_paras.append(text)

        # Include any remaining paragraphs
        if current_paras:
            pages.append(
                ParsedPage(
                    content="\n".join(current_paras),
                    section_header=current_section,
                )
            )

        # Also extract text from tables
        for table_idx, table in enumerate(doc.tables, start=1):
            table_rows: List[str] = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    table_rows.append(" | ".join(cells))
            if table_rows:
                pages.append(
                    ParsedPage(
                        content="\n".join(table_rows),
                        section_header=f"Table {table_idx}",
                        metadata={"is_table": True},
                    )
                )

        return ParsedDocument(
            filename=file_path.name,
            file_type="DOCX",
            pages=pages,
            metadata={"sections_count": len(pages)},
        )
