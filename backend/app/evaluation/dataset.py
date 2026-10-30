from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel


class BenchmarkQuery(BaseModel):
    id: str
    query: str
    category: str
    expected_entities: List[str]
    expected_answer_keywords: List[str]
    expected_relationships: List[str] = []
    gold_answer: str


BENCHMARK_DATASET: List[BenchmarkQuery] = [
    BenchmarkQuery(
        id="q1",
        query="What cloud infrastructure and database technologies are used by Project Phoenix?",
        category="multi_hop",
        expected_entities=["Project Phoenix", "PostgreSQL", "AWS", "Neo4j"],
        expected_answer_keywords=["project phoenix", "postgresql", "aws"],
        expected_relationships=["USES", "DEPLOYED_ON"],
        gold_answer="Project Phoenix utilizes PostgreSQL as its primary database and is deployed on AWS cloud infrastructure.",
    ),
    BenchmarkQuery(
        id="q2",
        query="Who is the primary owner or lead of Acme Corporation's Engineering department?",
        category="relationship",
        expected_entities=["Acme Corporation", "Engineering", "Alice Johnson"],
        expected_answer_keywords=["alice johnson", "engineering", "lead"],
        expected_relationships=["LEADS", "WORKS_FOR"],
        gold_answer="Alice Johnson leads the Engineering department at Acme Corporation.",
    ),
    BenchmarkQuery(
        id="q3",
        query="What is the enterprise password rotation and MFA security policy?",
        category="policy",
        expected_entities=["Security Policy", "MFA", "Password"],
        expected_answer_keywords=["mfa", "password", "rotation", "days"],
        gold_answer="The enterprise security policy requires multi-factor authentication (MFA) on all systems and password rotation every 90 days.",
    ),
    BenchmarkQuery(
        id="q4",
        query="Which projects and departments are connected to Bob Smith?",
        category="entity_centric",
        expected_entities=["Bob Smith", "Data Science", "Project Titan"],
        expected_answer_keywords=["bob smith", "data science"],
        expected_relationships=["CONTRIBUTES_TO", "MEMBER_OF"],
        gold_answer="Bob Smith is a member of the Data Science department and contributes to Project Titan.",
    ),
    BenchmarkQuery(
        id="q5",
        query="What was the total expenditure or budget allocated to Project Titan in 2024?",
        category="financial",
        expected_entities=["Project Titan", "2024"],
        expected_answer_keywords=["titan", "budget", "allocated"],
        gold_answer="Project Titan was allocated a budget of $1.5M for the fiscal year 2024.",
    ),
    BenchmarkQuery(
        id="q6",
        query="What are the details of the secret Project Zephyr unknown to the knowledge base?",
        category="insufficient_evidence",
        expected_entities=["Project Zephyr"],
        expected_answer_keywords=["couldn't find sufficient evidence", "insufficient evidence"],
        gold_answer="I couldn't find sufficient verified evidence in the available enterprise knowledge base to answer this question reliably.",
    ),
]
