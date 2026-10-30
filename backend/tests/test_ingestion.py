"""Unit tests for Document Ingestion, Parsing, and Chunking."""

from pathlib import Path
import pytest

from app.ingestion.chunker import TextChunker, StructureAwareChunker
from app.ingestion.parsers.base import ParsedDocument, ParsedPage
from app.ingestion.parsers.factory import ParserFactory
from app.ingestion.parsers.text_parser import TextParser
from app.ingestion.parsers.csv_parser import CSVParser


def test_text_parser(tmp_path: Path):
    """Test text and markdown parser."""
    md_file = tmp_path / "test_doc.md"
    md_file.write_text(
        "# Heading 1\nThis is paragraph one.\n\n## Heading 2\nThis is paragraph two.",
        encoding="utf-8",
    )

    parser = ParserFactory.get_parser(md_file)
    assert isinstance(parser, TextParser)

    parsed = parser.parse(md_file)
    assert parsed.filename == "test_doc.md"
    assert parsed.file_type == "MD"
    assert len(parsed.pages) >= 2


def test_csv_parser(tmp_path: Path):
    """Test tabular CSV parser converts rows to semantic text."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("Project,Owner,Status\nAlpha,Marcus,Active\nBeta,Elena,Planning\n", encoding="utf-8")

    parser = ParserFactory.get_parser(csv_file)
    assert isinstance(parser, CSVParser)

    parsed = parser.parse(csv_file)
    assert parsed.file_type == "CSV"
    assert len(parsed.pages) == 2
    assert "Alpha" in parsed.pages[0].content


def test_chunker_logic():
    """Test recursive character chunking with overlap."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    parsed_doc = ParsedDocument(
        filename="sample.txt",
        file_type="TXT",
        pages=[
            ParsedPage(
                content="Enterprise Knowledge Copilot provides hybrid GraphRAG. " * 5,
                page_number=1,
                section_header="Introduction",
            )
        ],
    )

    chunks = chunker.chunk_document(parsed_doc)
    assert len(chunks) > 1
    for ch in chunks:
        assert ch.char_count > 0
        assert ch.token_count > 0
        assert ch.page_number == 1
        assert ch.section_header == "Introduction"


def test_structure_aware_chunker_token_estimation():
    """Test accurate token estimation heuristic."""
    chunker = StructureAwareChunker()
    text = "Enterprise Knowledge Copilot platform"
    tokens = chunker.estimate_tokens(text)
    assert tokens == max(1, len(text) // 4)
    assert chunker.estimate_tokens("") == 0


def test_structure_aware_chunker_empty_handling():
    """Test chunker handles empty or whitespace text gracefully."""
    chunker = StructureAwareChunker()
    assert chunker.chunk_text("") == []
    assert chunker.chunk_text("   \n\n   ") == []
