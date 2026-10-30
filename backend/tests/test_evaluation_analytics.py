"""Tests for Evaluation benchmarks and Analytics dashboard."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_evaluation_benchmark_flow(async_client: AsyncClient):
    # 1. Fetch benchmark dataset
    bm_res = await async_client.get("/api/evaluation/benchmark")
    assert bm_res.status_code == 200
    dataset = bm_res.json()
    assert len(dataset) >= 5

    # 2. Run an evaluation run with limit 2 queries for speed
    run_res = await async_client.post(
        "/api/evaluation/run",
        json={"name": "Fast Test Benchmark", "limit_queries": 2},
    )
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "completed"
    assert run_data["total_queries"] == 2
    assert "avg_groundedness" in run_data
    run_id = run_data["id"]

    # 3. List evaluation runs
    runs_res = await async_client.get("/api/evaluation/runs")
    assert runs_res.status_code == 200
    runs_list = runs_res.json()
    assert len(runs_list) >= 1

    # 4. Get specific evaluation run details
    detail_res = await async_client.get(f"/api/evaluation/runs/{run_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["results"]) == 2


@pytest.mark.asyncio
async def test_dashboard_analytics_endpoint(async_client: AsyncClient):
    res = await async_client.get("/api/analytics/dashboard")
    assert res.status_code == 200
    data = res.json()

    assert "documents_total" in data
    assert "chunks_total" in data
    assert "entities_total" in data
    assert "relationships_total" in data
    assert "conversations_total" in data
    assert "avg_grounding_score" in data
    assert "department_distribution" in data
    assert "graph_status" in data
