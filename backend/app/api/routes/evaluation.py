from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.evaluation.dataset import BENCHMARK_DATASET, BenchmarkQuery
from app.evaluation.evaluator import GraphRAGEvaluator
from app.evaluation.schemas import (
    EvaluationResultItem,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationRunSummary,
)
from app.models.evaluation import EvaluationResult, EvaluationRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Evaluation & Benchmarks"])


def get_evaluator() -> GraphRAGEvaluator:
    return GraphRAGEvaluator()


@router.post("/run", response_model=EvaluationRunResponse)
async def run_evaluation(
    request: Optional[EvaluationRunRequest] = None,
    db: AsyncSession = Depends(get_db),
    evaluator: GraphRAGEvaluator = Depends(get_evaluator),
):
    """
    Trigger a full evaluation run across the enterprise benchmark dataset.
    Computes recall, precision, groundedness, citation coverage, hallucination rate, and latencies.
    """
    req = request or EvaluationRunRequest()
    return await evaluator.run_evaluation(db=db, request=req)


@router.get("/runs", response_model=List[EvaluationRunSummary])
async def list_evaluation_runs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List historical evaluation runs."""
    res = await db.execute(
        select(EvaluationRun)
        .order_by(desc(EvaluationRun.created_at))
        .limit(limit)
    )
    runs = res.scalars().all()
    return [
        EvaluationRunSummary(
            id=r.id,
            name=r.name,
            status=r.status,
            total_queries=r.total_queries,
            avg_groundedness=r.avg_groundedness,
            avg_citation_coverage=r.avg_citation_coverage,
            hallucination_rate=r.hallucination_rate,
            avg_latency_ms=r.avg_latency_ms,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full details and individual query metrics for an evaluation run."""
    res = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.id == run_id)
        .options(selectinload(EvaluationRun.results))
    )
    run = res.scalars().first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found.",
        )

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
            for r in (run.results or [])
        ],
    )


@router.get("/benchmark", response_model=List[BenchmarkQuery])
async def get_benchmark_dataset():
    """Retrieve the standard enterprise benchmark query dataset."""
    return BENCHMARK_DATASET
