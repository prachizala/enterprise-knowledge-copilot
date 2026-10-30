"""Plain text extraction with multi-encoding fallback."""

import logging
from pathlib import Path

from app.extraction.base import (
    BaseExtractor,
    EmptyContentError,
    ExtractionError,
    ExtractedContent,
)

logger = logging.getLogger(__name__)

ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]


class TxtExtractor(BaseExtractor):
    """Extracts text from plain text and markdown documents."""

    def extract(self, file_path: Path) -> ExtractedContent:
        if not file_path.is_file():
            raise ExtractionError(f"File not found: {file_path}")

        raw_bytes = file_path.read_bytes()
        if not raw_bytes:
            raise EmptyContentError("Text file is empty (0 bytes).")

        decoded_text: str = ""
        used_encoding: str = "utf-8"

        # Try standard encodings in sequence
        for enc in ENCODINGS_TO_TRY:
            try:
                decoded_text = raw_bytes.decode(enc)
                used_encoding = enc
                break
            except (UnicodeDecodeError, LookupError):
                continue

        # If all strict decodes fail, fall back to UTF-8 with replacement characters
        if not decoded_text:
            logger.warning(f"Using lossy replacement decode for '{file_path.name}'")
            decoded_text = raw_bytes.decode("utf-8", errors="replace")
            used_encoding = "utf-8-replace"

        cleaned_text = decoded_text.strip()
        if not cleaned_text:
            raise EmptyContentError("Text file contains no extractable content after trimming.")

        line_count = len(cleaned_text.splitlines())

        return ExtractedContent(
            text=cleaned_text,
            page_count=None,
            metadata={
                "source_format": "txt",
                "encoding": used_encoding,
                "line_count": line_count,
            },
        )
