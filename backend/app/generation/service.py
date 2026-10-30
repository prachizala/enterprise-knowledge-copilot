from __future__ import annotations

import logging
import time
from typing import AsyncGenerator, Optional, Sequence

from app.generation.base import LLMProvider
from app.generation.citation_extractor import CitationExtractor
from app.generation.factory import get_llm_provider
from app.generation.grounding_scorer import GroundingScorer
from app.generation.prompt_builder import PromptBuilder
from app.generation.schemas import Citation, GenerationResponse
from app.retrieval.schemas import GroundedContext

logger = logging.getLogger(__name__)


class LLMGenerationService:
    """
    Orchestrates the grounded answer generation lifecycle:
    1. Validates context and evidence availability
    2. Builds anti-injection prompt via PromptBuilder
    3. Calls LLMProvider (OpenAI or Mock fallback)
    4. Extracts and validates numerical citation markers [n]
    5. Calculates groundedness and faithfulness score
    6. Returns structured GenerationResponse
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        citation_extractor: Optional[CitationExtractor] = None,
        grounding_scorer: Optional[GroundingScorer] = None,
    ) -> None:
        self.provider = provider or get_llm_provider()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.citation_extractor = citation_extractor or CitationExtractor()
        self.grounding_scorer = grounding_scorer or GroundingScorer()

    async def generate_answer(
        self,
        query: str,
        grounded_context: GroundedContext,
        chat_history: Optional[Sequence[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> GenerationResponse:
        start_time = time.perf_counter()

        # If no evidence is present in context, generate faithful refusal directly
        if not grounded_context.has_evidence:
            refusal_text = (
                "I couldn't find sufficient verified evidence in the available enterprise "
                "knowledge base to answer this question reliably."
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return GenerationResponse(
                answer=refusal_text,
                citations=[],
                model=getattr(self.provider, "model", getattr(self.provider, "model_name", "mock")),
                provider=getattr(self.provider, "provider_name", getattr(self.provider, "name", "mock")),
                grounding_score=1.0,
                latency_ms=round(elapsed_ms, 2),
                tokens_used=15,
                has_insufficient_evidence=True,
            )

        # Build prompt messages
        messages = self.prompt_builder.build_messages(
            query=query,
            grounded_context=grounded_context,
            chat_history=chat_history,
        )

        try:
            # Call provider
            gen_res = await self.provider.generate(
                messages=messages,
                max_tokens=max_tokens or 1500,
                temperature=temperature or 0.1,
            )
            if isinstance(gen_res, tuple):
                raw_answer, tokens_used = gen_res
            else:
                raw_answer = str(gen_res)
                tokens_used = len(raw_answer.split()) * 2

            # Extract citations
            citations = self.citation_extractor.extract_citations(
                answer_text=raw_answer,
                fused_candidates=grounded_context.candidates,
                graph_paths=grounded_context.graph_paths,
            )

            # Score grounding
            grounding_score = self.grounding_scorer.score(
                answer=raw_answer,
                citations=citations,
                grounded_context=grounded_context,
            )

            has_insufficient_evidence = (
                "couldn't find sufficient evidence" in raw_answer.lower()
                or "insufficient evidence" in raw_answer.lower()
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return GenerationResponse(
                answer=raw_answer,
                citations=citations,
                model=getattr(self.provider, "model", getattr(self.provider, "model_name", "mock")),
                provider=getattr(self.provider, "provider_name", getattr(self.provider, "name", "mock")),
                grounding_score=grounding_score,
                latency_ms=round(elapsed_ms, 2),
                tokens_used=tokens_used,
                has_insufficient_evidence=has_insufficient_evidence,
            )

        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            # Safe grounded fallback on provider failure
            fallback_text = (
                f"An error occurred during response generation. However, based on retrieved enterprise documents, "
                f"relevant information was found in {len(grounded_context.candidates)} source excerpts."
            )
            return GenerationResponse(
                answer=fallback_text,
                citations=[],
                model=getattr(self.provider, "model", "fallback"),
                provider="fallback",
                grounding_score=0.5,
                latency_ms=round(elapsed_ms, 2),
                tokens_used=0,
                has_insufficient_evidence=False,
            )

    async def stream_answer(
        self,
        query: str,
        grounded_context: GroundedContext,
        chat_history: Optional[Sequence[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        if not grounded_context.has_evidence:
            yield "I couldn't find sufficient verified evidence in the available enterprise knowledge base to answer this question reliably."
            return

        messages = self.prompt_builder.build_messages(
            query=query,
            grounded_context=grounded_context,
            chat_history=chat_history,
        )

        async for chunk in self.provider.stream(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield chunk
