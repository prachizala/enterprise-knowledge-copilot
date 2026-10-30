"""Text and Markdown Document Parser."""

from pathlib import Path
from typing import List

from app.ingestion.parsers.base import BaseParser, ParsedDocument, ParsedPage


class TextParser(BaseParser):
    """Parses plain text (.txt) and Markdown (.md) documents."""

    def parse(self, file_path: Path) -> ParsedDocument:
        # Attempt reading with standard encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content = ""
        for enc in encodings:
            try:
                content = file_path.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        pages: List[ParsedPage] = []
        is_markdown = file_path.suffix.lower() == ".md"

        if is_markdown:
            # Split sections by markdown headers (#, ##, ###)
            lines = content.splitlines()
            current_header = "Introduction"
            current_chunk_lines: List[str] = []

            for line in lines:
                if line.startswith("#"):
                    if current_chunk_lines:
                        pages.append(
                            ParsedPage(
                                content="\n".join(current_chunk_lines).strip(),
                                section_header=current_header,
                            )
                        )
                        current_chunk_lines = []
                    current_header = line.lstrip("#").strip()
                else:
                    current_chunk_lines.append(line)

            if current_chunk_lines:
                pages.append(
                    ParsedPage(
                        content="\n".join(current_chunk_lines).strip(),
                        section_header=current_header,
                    )
                )
        else:
            # Plain text: preserve paragraphs or logical breaks
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [content.strip()] if content.strip() else []

            for idx, p in enumerate(paragraphs, start=1):
                pages.append(
                    ParsedPage(
                        content=p,
                        page_number=idx,
                    )
                )

        file_type = "MD" if is_markdown else "TXT"

        return ParsedDocument(
            filename=file_path.name,
            file_type=file_type,
            pages=pages,
            metadata={"character_count": len(content)},
        )
