from __future__ import annotations

import logging
import time
from typing import List, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.dataset import BENCHMARK_DATASET, BenchmarkQuery
from app.evaluation.schemas import (
    EvaluationResultItem,
    EvaluationRunRequest,
    EvaluationRunResponse,
)
from app.generation.service import LLMGenerationService
from app.models.evaluation import EvaluationResult, EvaluationRun
from app.retrieval.schemas import RetrievalSearchRequest
from app.retrieval.service import GraphRAGRetrievalService

logger = logging.getLogger(__name__)


class GraphRAGEvaluator:
    def __init__(
        self,
        retrieval_service: Optional[GraphRAGRetrievalService] = None,
        generation_service: Optional[LLMGenerationService] = None,
    ) -> None:
        self.retrieval_service = retrieval_service or GraphRAGRetrievalService()
        self.generation_service = generation_service or LLMGenerationService()

    async def run_evaluation(
        self,
        db: AsyncSession,
        request: EvaluationRunRequest,
    ) -> EvaluationRunResponse:
        run_id = str(uuid4())
        run = EvaluationRun(
            id=run_id,
            name=request.name,
            status="running",
        )
        db.add(run)
        await db.commit()

        dataset = BENCHMARK_DATASET
        if request.limit_queries:
            dataset = dataset[: request.limit_queries]

        results: List[EvaluationResult] = []
        recalls: List[float] = []
        precisions: List[float] = []
        groundedness_scores: List[float] = []
        citation_coverages: List[float] = []
        hallucinations: List[int] = []
        latencies: List[float] = []

        for item in dataset:
            query_start = time.perf_counter()

            # 1. Retrieval
            grounded_context = await self.retrieval_service.retrieve(
                db=db,
                query=item.query,
                top_k=5,
            )

            # 2. Generation
            gen_resp = await self.generation_service.generate_answer(
                query=item.query,
                grounded_context=grounded_context,
            )

            query_latency = (time.perf_counter() - query_start) * 1000
            latencies.append(query_latency)

            # 3. Compute Metrics
            actual_lower = gen_resp.answer.lower()

            # Precision & Recall based on expected entities / keywords
            if item.category == "insufficient_evidence":
                is_faithful_refusal = (
                    "couldn't find sufficient evidence" in actual_lower
                    or "insufficient evidence" in actual_lower
                )
                hallucinated = 0 if is_faithful_refusal else 1
                recall = 1.0 if is_faithful_refusal else 0.0
                precision = 1.0 if is_faithful_refusal else 0.0
                citation_cov = 1.0
            else:
                matched_keywords = sum(
                    1 for kw in item.expected_answer_keywords if kw in actual_lower
                )
                recall = matched_keywords / max(1, len(item.expected_answer_keywords))

                retrieved_text = grounded_context.formatted_context.lower()
                matched_entities = sum(
                    1 for e in item.expected_entities if e.lower() in retrieved_text
                )
                precision = matched_entities / max(1, len(item.expected_entities))

                citation_cov = 1.0 if gen_resp.citations else (0.5 if not grounded_context.has_evidence else 0.0)
                hallucinated = 1 if (not grounded_context.has_evidence and len(actual_lower) > 50 and not gen_resp.has_insufficient_evidence) else 0

            recalls.append(recall)
            precisions.append(precision)
            groundedness_scores.append(gen_resp.grounding_score)
            citation_coverages.append(citation_cov)
            hallucinations.append(hallucinated)

            res_model = EvaluationResult(
                id=str(uuid4()),
                run_id=run_id,
                query=item.query,
                expected_answer=item.gold_answer,
                actual_answer=gen_resp.answer,
                groundedness_score=gen_resp.grounding_score,
                citation_coverage=citation_cov,
                latency_ms=round(query_latency, 2),
                metrics={
                    "category": item.category,
                    "recall": round(recall, 2),
                    "precision": round(precision, 2),
                    "hallucinated": hallucinated,
                    "citations_count": len(gen_resp.citations),
                    "provider": gen_resp.provider,
                },
            )
            db.add(res_model)
            results.append(res_model)

        # Compute aggregate averages
        n = max(1, len(dataset))
        run.total_queries = len(dataset)
        run.avg_recall = round(sum(recalls) / n, 2)
        run.avg_precision = round(sum(precisions) / n, 2)
        run.avg_groundedness = round(sum(groundedness_scores) / n, 2)
        run.avg_citation_coverage = round(sum(citation_coverages) / n, 2)
        run.hallucination_rate = round(sum(hallucinations) / n, 2)
        run.avg_latency_ms = round(sum(latencies) / n, 2)
        run.status = "completed"

        await db.commit()
        await db.refresh(run)

        return EvaluationRunResponse(
            id=run.id,
            name=run.name,
            status=run.status,
            total_queries=run.total_queries,
            avg_recall=run.avg_recall,
            avg_precision=run.avg_precision,
            avg_groundedness=run.avg_groundedness,
            avg_citation_coverage=run.avg_citation_coverage,
            hallucination_rate=run.hallucination_rate,
            avg_latency_ms=run.avg_latency_ms,
            created_at=run.created_at,
            results=[
                EvaluationResultItem(
                    id=r.id,
                    query=r.query,
                    expected_answer=r.expected_answer,
                    actual_answer=r.actual_answer,
                    groundedness_score=r.groundedness_score,
                    citation_coverage=r.citation_coverage,
                    latency_ms=r.latency_ms,
                    metrics=r.metrics,
                    created_at=r.created_at,
                )
                for r in results
            ],
        )
