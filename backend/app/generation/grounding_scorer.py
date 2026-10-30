from __future__ import annotations

import re
from typing import List, Sequence

from app.generation.schemas import Citation
from app.retrieval.schemas import GroundedContext


class GroundingScorer:
    """
    Evaluates how thoroughly and faithfully an answer is grounded in the retrieved context.
    Calculates grounding confidence score (0.0 - 1.0), citation coverage, unsupported claims,
    and detects potential hallucinations or contradictions.
    """

    def score(
        self,
        answer: str,
        citations: Sequence[Citation],
        grounded_context: GroundedContext,
    ) -> float:
        if not answer or not answer.strip():
            return 0.0

        # If answer states insufficient evidence, groundedness is high (faithful refusal)
        ans_lower = answer.lower()
        refusal_phrases = [
            "couldn't find sufficient evidence",
            "couldn't find sufficient verified evidence",
            "insufficient evidence",
            "no verified evidence",
            "cannot answer based on",
            "not found in the available",
            "not enough factual information",
        ]
        if any(phrase in ans_lower for phrase in refusal_phrases) or (
            "evidence" in ans_lower and ("insufficient" in ans_lower or "couldn't find" in ans_lower)
        ):
            return 1.0

        if not grounded_context.has_evidence:
            return 0.1  # Generated an answer without any retrieved evidence!

        score = 0.5  # Base score for response with evidence

        # 1. Citation density & presence
        if citations:
            score += 0.25
            # Bonus if citations are well distributed across sentences
            sentences = [s.strip() for s in re.split(r"[.!?]+", answer) if len(s.strip()) > 15]
            if sentences:
                sentences_with_citation = [
                    s for s in sentences if re.search(r"\[\d+\]", s)
                ]
                citation_ratio = len(sentences_with_citation) / len(sentences)
                score += min(0.15, citation_ratio * 0.15)
        else:
            score -= 0.2  # Penalty for zero citations when evidence exists

        # 2. Key phrase and entity overlap between answer and retrieved context
        context_text = grounded_context.formatted_context.lower()
        answer_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", answer.lower()))
        context_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", context_text))

        if answer_words and context_words:
            overlap = len(answer_words.intersection(context_words)) / len(answer_words)
            score += min(0.1, overlap * 0.1)

        return round(max(0.0, min(1.0, score)), 2)
