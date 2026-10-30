"""Structure-aware semantic text chunking engine for Enterprise RAG.

Preserves:
- Document Page Boundaries (e.g. PDF 'Page X\n---------')
- Heading and Section Hierarchies (Markdown '#', '##', '###', '####')
- Tabular structures ('[Table]' blocks and markdown tables)
- Tabular record grouping ('[Record X]' blocks)
- Natural paragraph and sentence boundaries with configurable overlap
- Accurate token estimation (~4 chars/token) and provenance metadata
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.ingestion.parsers.base import ParsedDocument, ParsedPage


@dataclass
class Chunk:
    """Represents a discrete indexed text chunk for hybrid retrieval."""
    index: int
    content: str
    char_count: int
    token_count: int
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructureAwareChunker:
    """Splits structured and unstructured text into overlapping semantic chunks with full provenance."""

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        min_chunk_size: int = 80,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = min(chunk_overlap, chunk_size // 2)
        self.min_chunk_size = min_chunk_size

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (standard heuristic ~4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _split_into_pages(self, text: str) -> List[Tuple[Optional[int], str]]:
        """Identify page boundaries like 'Page 1\n---------' or return single page block."""
        page_pattern = re.compile(
            r"(?:^|\n\n)(?:Page\s+(\d+)\s*\n[-=]{3,}\n?)",
            re.IGNORECASE,
        )
        matches = list(page_pattern.finditer(text))
        if not matches:
            return [(None, text)]

        pages: List[Tuple[Optional[int], str]] = []
        for i, match in enumerate(matches):
            page_num = int(match.group(1))
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            page_text = text[start_pos:end_pos].strip()
            if page_text:
                pages.append((page_num, page_text))

        return pages if pages else [(None, text)]

    def _split_into_sections(self, page_text: str) -> List[Tuple[Optional[str], str, Dict[str, Any]]]:
        """Split a page's text into sections based on headings (#, ##, ###, [Table], [Record])."""
        section_pattern = re.compile(
            r"(?:^|\n)(?=(?:#{1,6}\s+|\[Table\]|\[Record\s+\d+\]))",
            re.MULTILINE,
        )
        raw_sections = [s.strip() for s in section_pattern.split(page_text) if s.strip()]
        if not raw_sections:
            return [(None, page_text.strip(), {})]

        sections: List[Tuple[Optional[str], str, Dict[str, Any]]] = []
        current_heading: Optional[str] = None
        heading_stack: List[str] = []

        for sec in raw_sections:
            meta: Dict[str, Any] = {}
            first_line = sec.split("\n", 1)[0].strip()

            if first_line.startswith("#"):
                # Markdown heading
                level = len(first_line) - len(first_line.lstrip("#"))
                heading_text = first_line.lstrip("#").strip()
                # Maintain heading stack for hierarchy
                if level <= len(heading_stack):
                    heading_stack = heading_stack[:level - 1]
                heading_stack.append(heading_text)
                current_heading = " > ".join(heading_stack) if len(heading_stack) > 1 else heading_text
                meta["heading_level"] = level
                meta["headings_path"] = list(heading_stack)
            elif first_line.startswith("[Table]"):
                meta["is_table"] = True
                if not current_heading:
                    current_heading = "Table"
            elif first_line.startswith("[Record"):
                meta["is_record"] = True
                rec_match = re.search(r"\[Record\s+(\d+)\]", first_line)
                if rec_match:
                    meta["record_index"] = int(rec_match.group(1))

            sections.append((current_heading, sec, meta))

        return sections

    def _chunk_text_block(
        self,
        block_text: str,
        page_number: Optional[int],
        section_header: Optional[str],
        base_meta: Dict[str, Any],
    ) -> List[Chunk]:
        """Split a coherent text block into chunks respecting chunk_size and chunk_overlap."""
        if base_meta.get("is_table"):
            return self._chunk_table_block(block_text, page_number, section_header, base_meta)
        if base_meta.get("is_record"):
            return self._chunk_record_block(block_text, page_number, section_header, base_meta)

        # Standard prose: split by paragraphs (\n\n)
        paragraphs = [p.strip() for p in block_text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        chunks: List[Chunk] = []
        current_pieces: List[str] = []
        current_len = 0

        for para in paragraphs:
            # If paragraph itself is larger than chunk_size, split by sentences
            if len(para) > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                para_pieces = [s.strip() for s in sentences if s.strip()]
            else:
                para_pieces = [para]

            for piece in para_pieces:
                piece_len = len(piece) + (2 if current_pieces else 0)
                if current_len + piece_len > self.chunk_size and current_pieces:
                    chunk_text = "\n\n".join(current_pieces).strip()
                    if chunk_text:
                        chunks.append(
                            Chunk(
                                index=0,  # Will be reassigned globally
                                content=chunk_text,
                                char_count=len(chunk_text),
                                token_count=self.estimate_tokens(chunk_text),
                                page_number=page_number,
                                section_header=section_header,
                                metadata=dict(base_meta),
                            )
                        )

                    # Compute overlap from trailing pieces
                    overlap_len = 0
                    overlap_pieces: List[str] = []
                    for prev_p in reversed(current_pieces):
                        if overlap_len + len(prev_p) <= self.chunk_overlap:
                            overlap_pieces.insert(0, prev_p)
                            overlap_len += len(prev_p)
                        else:
                            break

                    current_pieces = overlap_pieces
                    current_len = sum(len(p) for p in current_pieces)

                current_pieces.append(piece)
                current_len += len(piece)

        if current_pieces:
            chunk_text = "\n\n".join(current_pieces).strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        index=0,
                        content=chunk_text,
                        char_count=len(chunk_text),
                        token_count=self.estimate_tokens(chunk_text),
                        page_number=page_number,
                        section_header=section_header,
                        metadata=dict(base_meta),
                    )
                )

        return chunks

    def _chunk_table_block(
        self,
        table_text: str,
        page_number: Optional[int],
        section_header: Optional[str],
        base_meta: Dict[str, Any],
    ) -> List[Chunk]:
        """Keep table intact or split cleanly by rows if exceeding chunk_size."""
        if len(table_text) <= self.chunk_size:
            return [
                Chunk(
                    index=0,
                    content=table_text,
                    char_count=len(table_text),
                    token_count=self.estimate_tokens(table_text),
                    page_number=page_number,
                    section_header=section_header,
                    metadata={**base_meta, "is_table": True},
                )
            ]

        # Table exceeds chunk size: split by lines/rows
        lines = [line.strip() for line in table_text.splitlines() if line.strip()]
        header_lines = [lines[0]] if lines and lines[0] == "[Table]" else []
        if len(lines) > 1 and lines[0] == "[Table]":
            header_lines.append(lines[1])
            data_lines = lines[2:]
        else:
            data_lines = lines

        chunks: List[Chunk] = []
        current_rows = list(header_lines)
        current_len = sum(len(h) + 1 for h in header_lines)

        for row in data_lines:
            row_len = len(row) + 1
            if current_len + row_len > self.chunk_size and len(current_rows) > len(header_lines):
                chunk_str = "\n".join(current_rows)
                chunks.append(
                    Chunk(
                        index=0,
                        content=chunk_str,
                        char_count=len(chunk_str),
                        token_count=self.estimate_tokens(chunk_str),
                        page_number=page_number,
                        section_header=section_header,
                        metadata={**base_meta, "is_table": True},
                    )
                )
                current_rows = list(header_lines)
                current_len = sum(len(h) + 1 for h in header_lines)

            current_rows.append(row)
            current_len += row_len

        if current_rows and len(current_rows) > len(header_lines):
            chunk_str = "\n".join(current_rows)
            chunks.append(
                Chunk(
                    index=0,
                    content=chunk_str,
                    char_count=len(chunk_str),
                    token_count=self.estimate_tokens(chunk_str),
                    page_number=page_number,
                    section_header=section_header,
                    metadata={**base_meta, "is_table": True},
                )
            )

        return chunks if chunks else [
            Chunk(
                index=0,
                content=table_text,
                char_count=len(table_text),
                token_count=self.estimate_tokens(table_text),
                page_number=page_number,
                section_header=section_header,
                metadata={**base_meta, "is_table": True},
            )
        ]

    def _chunk_record_block(
        self,
        record_text: str,
        page_number: Optional[int],
        section_header: Optional[str],
        base_meta: Dict[str, Any],
    ) -> List[Chunk]:
        """Preserve record block boundaries."""
        return [
            Chunk(
                index=0,
                content=record_text,
                char_count=len(record_text),
                token_count=self.estimate_tokens(record_text),
                page_number=page_number,
                section_header=section_header or "Tabular Record",
                metadata={**base_meta, "is_record": True},
            )
        ]

    def chunk_text(
        self,
        text: str,
        file_type: str = "txt",
        document_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Convert extracted text into an ordered, structure-aware list of discrete chunks."""
        cleaned = text.strip()
        if not cleaned:
            return []

        doc_meta = document_metadata or {}
        doc_meta.setdefault("file_type", file_type.lower())

        pages = self._split_into_pages(cleaned)
        all_chunks: List[Chunk] = []

        for page_num, page_content in pages:
            sections = self._split_into_sections(page_content)
            
            # Check if sections are records that can be grouped together
            accumulated_records: List[str] = []
            accumulated_indices: List[int] = []
            current_record_len = 0
            
            for section_header, section_text, section_meta in sections:
                if section_meta.get("is_record"):
                    rec_idx = section_meta.get("record_index")
                    if current_record_len + len(section_text) + 2 > self.chunk_size and accumulated_records:
                        # Flush grouped records chunk
                        grouped_content = "\n\n".join(accumulated_records)
                        all_chunks.append(
                            Chunk(
                                index=0,
                                content=grouped_content,
                                char_count=len(grouped_content),
                                token_count=self.estimate_tokens(grouped_content),
                                page_number=page_num,
                                section_header="Tabular Records",
                                metadata={
                                    **doc_meta,
                                    "is_record_group": True,
                                    "record_range": [accumulated_indices[0], accumulated_indices[-1]],
                                },
                            )
                        )
                        accumulated_records = []
                        accumulated_indices = []
                        current_record_len = 0

                    accumulated_records.append(section_text)
                    if rec_idx:
                        accumulated_indices.append(rec_idx)
                    current_record_len += len(section_text) + 2
                    continue
                else:
                    # If we had accumulated records before hitting a non-record section, flush them
                    if accumulated_records:
                        grouped_content = "\n\n".join(accumulated_records)
                        all_chunks.append(
                            Chunk(
                                index=0,
                                content=grouped_content,
                                char_count=len(grouped_content),
                                token_count=self.estimate_tokens(grouped_content),
                                page_number=page_num,
                                section_header="Tabular Records",
                                metadata={
                                    **doc_meta,
                                    "is_record_group": True,
                                    "record_range": [accumulated_indices[0], accumulated_indices[-1]],
                                },
                            )
                        )
                        accumulated_records = []
                        accumulated_indices = []
                        current_record_len = 0

                merged_meta = {**doc_meta, **section_meta}
                if page_num is not None:
                    merged_meta["page_number"] = page_num
                if section_header:
                    merged_meta["section_header"] = section_header

                sec_chunks = self._chunk_text_block(
                    block_text=section_text,
                    page_number=page_num,
                    section_header=section_header,
                    base_meta=merged_meta,
                )
                all_chunks.extend(sec_chunks)

            # Flush trailing accumulated records if any
            if accumulated_records:
                grouped_content = "\n\n".join(accumulated_records)
                all_chunks.append(
                    Chunk(
                        index=0,
                        content=grouped_content,
                        char_count=len(grouped_content),
                        token_count=self.estimate_tokens(grouped_content),
                        page_number=page_num,
                        section_header="Tabular Records",
                        metadata={
                            **doc_meta,
                            "is_record_group": True,
                            "record_range": [accumulated_indices[0], accumulated_indices[-1]] if accumulated_indices else None,
                        },
                    )
                )

        # Assign global sequential indices
        for idx, chunk in enumerate(all_chunks):
            chunk.index = idx

        return all_chunks

    def chunk_document(self, parsed_doc: ParsedDocument) -> List[Chunk]:
        """Convert a ParsedDocument into an indexed list of chunks (for parser compatibility)."""
        all_chunks: List[Chunk] = []
        global_index = 0

        for page in parsed_doc.pages:
            text = page.content.strip()
            if not text:
                continue

            page_chunks = self.chunk_text(
                text=text,
                file_type=parsed_doc.file_type,
                document_metadata={
                    **parsed_doc.metadata,
                    **page.metadata,
                    "filename": parsed_doc.filename,
                },
            )

            for chunk in page_chunks:
                if page.page_number is not None:
                    chunk.page_number = page.page_number
                if page.section_header and not chunk.section_header:
                    chunk.section_header = page.section_header

                chunk.index = global_index
                all_chunks.append(chunk)
                global_index += 1

        return all_chunks


class TextChunker(StructureAwareChunker):
    """Backwards-compatible wrapper providing StructureAwareChunker functionality."""
    pass
