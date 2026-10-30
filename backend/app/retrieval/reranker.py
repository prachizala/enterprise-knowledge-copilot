"""Reranker abstraction and deterministic enterprise relevance reranker."""

import re
from abc import ABC, abstractmethod
from typing import List, Set
from app.retrieval.schemas import FusedCandidate, LinkedEntity


class BaseReranker(ABC):
    """Abstract base class for retrieval candidates reranking."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: List[FusedCandidate],
        linked_entities: List[LinkedEntity],
        top_n: int = 10,
    ) -> List[FusedCandidate]:
        """Rerank candidates based on multi-signal relevance scoring."""
        pass


class DeterministicReranker(BaseReranker):
    """High-performance, deterministic reranker using lexical overlap, entity mentions, and hybrid synergy."""

    async def rerank(
        self,
        query: str,
        candidates: List[FusedCandidate],
        linked_entities: List[LinkedEntity],
        top_n: int = 10,
    ) -> List[FusedCandidate]:
        if not candidates:
            return []

        query_tokens = set(re.findall(r"\b\w{3,}\b", query.lower()))
        entity_names: Set[str] = {le.canonical_name.lower() for le in linked_entities} | {
            le.display_name.lower() for le in linked_entities
        }

        for cand in candidates:
            content_lower = cand.content.lower()
            content_tokens = set(re.findall(r"\b\w{3,}\b", content_lower))

            # 1. Lexical overlap score (0.0 - 1.0)
            overlap = len(query_tokens & content_tokens)
            lexical_score = overlap / max(len(query_tokens), 1)

            # 2. Entity match score
            entity_matches = sum(1 for name in entity_names if name in content_lower)
            entity_score = min(1.0, entity_matches * 0.4)

            # 3. Hybrid synergy bonus (multi-modal retrieval agreement)
            if cand.origin == "tri-hybrid":
                hybrid_bonus = 0.35
            elif cand.origin == "hybrid":
                hybrid_bonus = 0.25
            elif cand.origin in ("graph", "sparse"):
                hybrid_bonus = 0.10
            else:
                hybrid_bonus = 0.0

            # 4. Section header match bonus
            header_bonus = 0.0
            if cand.section_title and any(t in cand.section_title.lower() for t in query_tokens):
                header_bonus = 0.15

            # Combine signals
            boosted_score = (
                (cand.final_score * 0.45)
                + (lexical_score * 0.25)
                + (entity_score * 0.20)
                + hybrid_bonus
                + header_bonus
            )
            cand.final_score = round(boosted_score, 4)

        # Sort descending by final boosted score
        candidates.sort(key=lambda c: c.final_score, reverse=True)
        return candidates[:top_n]
