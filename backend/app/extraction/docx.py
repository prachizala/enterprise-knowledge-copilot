"""DOCX text extraction using python-docx with structural element preservation."""

import logging
from pathlib import Path
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.extraction.base import (
    BaseExtractor,
    CorruptDocumentError,
    EmptyContentError,
    ExtractionError,
    ExtractedContent,
)

logger = logging.getLogger(__name__)


class DocxExtractor(BaseExtractor):
    """Extracts structured text from Microsoft Word DOCX files."""

    def extract(self, file_path: Path) -> ExtractedContent:
        if not file_path.is_file():
            raise ExtractionError(f"File not found: {file_path}")

        try:
            doc = Document(str(file_path))
        except Exception as exc:
            logger.error(f"Failed to parse DOCX '{file_path.name}': {exc}")
            raise CorruptDocumentError(f"Cannot parse DOCX file: {exc}") from exc

        body_elements = []

        try:
            # Iterate through body elements in document order (paragraphs and tables)
            for child in doc.element.body:
                if child.tag.endswith("p"):
                    p = Paragraph(child, doc)
                    text = p.text.strip()
                    if text:
                        style_name = p.style.name if p.style else ""
                        if style_name.startswith("Heading 1"):
                            body_elements.append(f"# {text}")
                        elif style_name.startswith("Heading 2"):
                            body_elements.append(f"## {text}")
                        elif style_name.startswith("Heading 3"):
                            body_elements.append(f"### {text}")
                        elif style_name.startswith("Heading"):
                            body_elements.append(f"#### {text}")
                        else:
                            body_elements.append(text)

                elif child.tag.endswith("tbl"):
                    tbl = Table(child, doc)
                    table_rows = []
                    for row in tbl.rows:
                        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        if any(row_cells):
                            table_rows.append(" | ".join(row_cells))
                    if table_rows:
                        table_repr = "\n".join(table_rows)
                        body_elements.append(f"\n[Table]\n{table_repr}\n")

        except Exception as exc:
            logger.error(f"Error while reading DOCX structure in '{file_path.name}': {exc}")
            raise ExtractionError(f"DOCX extraction failed: {exc}") from exc

        # Fallback if body iteration produced nothing: read doc.paragraphs directly
        if not body_elements:
            for p in doc.paragraphs:
                txt = p.text.strip()
                if txt:
                    body_elements.append(txt)

        full_text = "\n\n".join(body_elements).strip()
        if not full_text:
            raise EmptyContentError("DOCX document contains no text content.")

        return ExtractedContent(
            text=full_text,
            page_count=None,
            metadata={"source_format": "docx", "elements_count": len(body_elements)},
        )
