"""PDF text extraction using pypdf with page boundary preservation."""

import logging
from pathlib import Path
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.extraction.base import (
    BaseExtractor,
    CorruptDocumentError,
    EmptyContentError,
    ExtractionError,
    ExtractedContent,
)

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    """Extracts text from PDF documents preserving page boundaries."""

    def extract(self, file_path: Path) -> ExtractedContent:
        if not file_path.is_file():
            raise ExtractionError(f"File not found: {file_path}")

        try:
            reader = PdfReader(str(file_path))
        except PdfReadError as exc:
            logger.error(f"Corrupt PDF file '{file_path.name}': {exc}")
            raise CorruptDocumentError(f"Cannot read PDF file: {exc}") from exc
        except Exception as exc:
            logger.error(f"Failed to open PDF '{file_path.name}': {exc}")
            raise ExtractionError(f"Failed to open PDF: {exc}") from exc

        page_count = len(reader.pages)
        if page_count == 0:
            raise EmptyContentError("PDF document has 0 pages.")

        page_texts = []
        total_extracted_chars = 0

        for idx, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception as page_exc:
                logger.warning(f"Error extracting text from page {idx} in {file_path.name}: {page_exc}")
                page_text = ""

            cleaned_page = page_text.strip()
            if cleaned_page:
                total_extracted_chars += len(cleaned_page)
                page_section = f"Page {idx}\n---------\n{cleaned_page}"
                page_texts.append(page_section)

        if total_extracted_chars == 0 or not page_texts:
            raise EmptyContentError(
                "PDF contains no extractable text. Scanned image-only PDFs or empty files are not supported in this step."
            )

        full_text = "\n\n".join(page_texts)

        return ExtractedContent(
            text=full_text,
            page_count=page_count,
            metadata={"source_format": "pdf", "page_count": page_count},
        )
