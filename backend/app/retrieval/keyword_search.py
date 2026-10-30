"""Lexical / BM25 keyword search service for Sparse retrieval in Tri-Hybrid GraphRAG."""

import logging
import math
import re
from typing import Dict, List, Optional, Set
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import build_accessible_documents_filter
from app.models.document import Document, DocumentChunk
from app.retrieval.schemas import SparseCandidate

logger = logging.getLogger(__name__)

STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves",
}


def tokenize(text: str) -> List[str]:
    """Tokenize input text into lowercase alphanumeric keywords."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


class KeywordSearchService:
    """Performs sparse keyword / BM25 lexical searches over document chunks."""

    @classmethod
    async def search_candidates(
        cls,
        db: AsyncSession,
        query: str,
        user: Optional[object] = None,
        top_k: int = 10,
        department: Optional[str] = None,
        document_id: Optional[str] = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> List[SparseCandidate]:
        """Retrieve SparseCandidate items using Okapi BM25 scoring with RBAC filtering."""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # 1. Base query on DocumentChunk joined with Document
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
        )

        # Enforce RBAC
        if user is not None:
            rbac_filter = build_accessible_documents_filter(user)
            if rbac_filter is not None:
                stmt = stmt.where(rbac_filter)

        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        if department:
            stmt = stmt.where(Document.department.ilike(department))

        # Match chunks that contain at least one query token
        ilike_clauses = [
            DocumentChunk.content.ilike(f"%{tok}%") for tok in query_tokens[:8]
        ]
        if ilike_clauses:
            stmt = stmt.where(or_(*ilike_clauses))

        # Limit candidate pool for BM25 reranking
        stmt = stmt.limit(top_k * 5)
        rows = (await db.execute(stmt)).all()

        if not rows:
            return []

        # 2. Compute BM25 statistics over candidate pool
        total_docs = len(rows)
        doc_lengths: List[int] = []
        doc_token_counts: List[Dict[str, int]] = []
        doc_matched_tokens: List[List[str]] = []

        doc_freq: Dict[str, int] = {tok: 0 for tok in query_tokens}

        for chunk, doc in rows:
            chunk_tokens = tokenize(chunk.content)
            doc_len = len(chunk_tokens)
            doc_lengths.append(doc_len)

            tf: Dict[str, int] = {}
            matched = []
            for tok in chunk_tokens:
                tf[tok] = tf.get(tok, 0) + 1

            for q_tok in query_tokens:
                if q_tok in tf:
                    doc_freq[q_tok] = doc_freq.get(q_tok, 0) + 1
                    matched.append(q_tok)

            doc_token_counts.append(tf)
            doc_matched_tokens.append(list(set(matched)))

        avg_doc_len = (sum(doc_lengths) / total_docs) if total_docs > 0 else 1.0

        # Compute IDF for query tokens
        idf: Dict[str, float] = {}
        for q_tok in query_tokens:
            df = doc_freq.get(q_tok, 0)
            idf[q_tok] = math.log(((total_docs - df + 0.5) / (df + 0.5)) + 1.0)

        # 3. Calculate BM25 scores
        scored_candidates: List[SparseCandidate] = []
        raw_scores: List[float] = []

        for idx, (chunk, doc) in enumerate(rows):
            tf = doc_token_counts[idx]
            doc_len = doc_lengths[idx]
            matched = doc_matched_tokens[idx]

            bm25 = 0.0
            for q_tok in query_tokens:
                freq = tf.get(q_tok, 0)
                if freq > 0:
                    numerator = freq * (k1 + 1.0)
                    denominator = freq + k1 * (1.0 - b + b * (doc_len / avg_doc_len))
                    bm25 += idf[q_tok] * (numerator / denominator)

            raw_scores.append(bm25)
            scored_candidates.append(
                SparseCandidate(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    document_title=doc.original_filename or doc.filename,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section_title=chunk.section_header,
                    content=chunk.content,
                    bm25_score=bm25,
                    matched_terms=matched,
                    department=doc.department,
                    content_hash=chunk.content_hash,
                )
            )

        # 4. Normalize scores to [0.0, 1.0] and filter top_k
        max_score = max(raw_scores) if raw_scores else 1.0
        if max_score > 0:
            for cand in scored_candidates:
                cand.bm25_score = round(cand.bm25_score / max_score, 4)

        scored_candidates.sort(key=lambda c: c.bm25_score, reverse=True)
        return scored_candidates[:top_k]
