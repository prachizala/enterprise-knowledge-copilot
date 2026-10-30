"""CSV tabular text extraction into structured key-value line blocks."""

import csv
import io
import logging
from pathlib import Path

from app.extraction.base import (
    BaseExtractor,
    CorruptDocumentError,
    EmptyContentError,
    ExtractionError,
    ExtractedContent,
)

logger = logging.getLogger(__name__)


class CSVExtractor(BaseExtractor):
    """Extracts structured text from CSV tables preserving column key-value semantics."""

    def extract(self, file_path: Path) -> ExtractedContent:
        if not file_path.is_file():
            raise ExtractionError(f"File not found: {file_path}")

        raw_bytes = file_path.read_bytes()
        if not raw_bytes:
            raise EmptyContentError("CSV file is empty (0 bytes).")

        # Decode with fallback encodings
        text_content = ""
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                text_content = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not text_content:
            text_content = raw_bytes.decode("utf-8", errors="replace")

        # Determine delimiter using Sniffer if possible
        stream = io.StringIO(text_content.strip())
        sample = text_content[:2048]
        delimiter = ","
        try:
            sniffer = csv.Sniffer()
            has_header = sniffer.has_header(sample)
            dialect = sniffer.sniff(sample)
            delimiter = dialect.delimiter
        except Exception:
            has_header = True

        stream.seek(0)
        reader = csv.reader(stream, delimiter=delimiter)

        try:
            rows = list(reader)
        except Exception as exc:
            logger.error(f"Failed to read CSV '{file_path.name}': {exc}")
            raise CorruptDocumentError(f"Malformed CSV content: {exc}") from exc

        if not rows:
            raise EmptyContentError("CSV file contains no readable rows.")

        # Identify headers
        header_row = rows[0]
        data_rows = rows[1:]

        # Clean header labels
        headers = [h.strip() if h.strip() else f"Column_{i+1}" for i, h in enumerate(header_row)]

        if not data_rows:
            # If only headers exist without data rows, check if header has values
            if all(not h for h in headers):
                raise EmptyContentError("CSV file has no data rows or values.")
            # At least format headers
            formatted_blocks = ["Headers: " + ", ".join(headers)]
        else:
            formatted_blocks = []
            for row_idx, row in enumerate(data_rows, start=1):
                if not any(cell.strip() for cell in row):
                    continue  # skip completely empty lines

                row_lines = [f"[Record {row_idx}]"]
                for i, header in enumerate(headers):
                    val = row[i].strip() if i < len(row) else ""
                    if val:
                        row_lines.append(f"{header}: {val}")
                if len(row_lines) > 1:
                    formatted_blocks.append("\n".join(row_lines))

        if not formatted_blocks:
            raise EmptyContentError("CSV contains no valid text records.")

        full_text = "\n\n".join(formatted_blocks)

        return ExtractedContent(
            text=full_text,
            page_count=None,
            metadata={
                "source_format": "csv",
                "columns": headers,
                "record_count": len(formatted_blocks),
            },
        )
