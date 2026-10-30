from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    name: str = Field("Standard Benchmark", description="Benchmark run title")
    limit_queries: Optional[int] = Field(None, ge=1, le=20, description="Max queries to evaluate")


class EvaluationResultItem(BaseModel):
    id: str
    query: str
    expected_answer: Optional[str] = None
    actual_answer: str
    groundedness_score: float
    citation_coverage: float
    latency_ms: float
    metrics: Optional[Dict[str, Any]] = None
    created_at: datetime


class EvaluationRunResponse(BaseModel):
    id: str
    name: str
    status: str
    total_queries: int
    avg_recall: float
    avg_precision: float
    avg_groundedness: float
    avg_citation_coverage: float
    hallucination_rate: float
    avg_latency_ms: float
    created_at: datetime
    results: List[EvaluationResultItem] = []


class EvaluationRunSummary(BaseModel):
    id: str
    name: str
    status: str
    total_queries: int
    avg_groundedness: float
    avg_citation_coverage: float
    hallucination_rate: float
    avg_latency_ms: float
    created_at: datetime
