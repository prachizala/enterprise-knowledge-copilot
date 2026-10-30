"""CSV and Tabular Document Parser."""

import csv
from pathlib import Path
from typing import List

from app.ingestion.parsers.base import BaseParser, ParsedDocument, ParsedPage


class CSVParser(BaseParser):
    """Parses tabular CSV files into contextual semantic text records."""

    def parse(self, file_path: Path) -> ParsedDocument:
        pages: List[ParsedPage] = []
        encodings = ["utf-8", "utf-8-sig", "latin-1"]

        lines = []
        for enc in encodings:
            try:
                with open(file_path, mode="r", encoding=enc) as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames or []
                    for idx, row in enumerate(reader, start=1):
                        row_items = [
                            f"{k}: {v}" for k, v in row.items() if k and v and v.strip()
                        ]
                        if row_items:
                            text_rep = f"Row {idx} ({', '.join(fieldnames)}): " + "; ".join(row_items)
                            pages.append(
                                ParsedPage(
                                    content=text_rep,
                                    page_number=idx,
                                    metadata={"row_index": idx},
                                )
                            )
                break
            except (UnicodeDecodeError, csv.Error):
                continue

        return ParsedDocument(
            filename=file_path.name,
            file_type="CSV",
            pages=pages,
            metadata={"rows_count": len(pages)},
        )
