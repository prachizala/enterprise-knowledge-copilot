"""Tests for Grounded Answer Generation, Citations, and Faithfulness Scoring."""

import pytest
from app.generation.citation_extractor import CitationExtractor
from app.generation.grounding_scorer import GroundingScorer
from app.generation.mock_provider import MockLLMProvider
from app.generation.prompt_builder import PromptBuilder
from app.generation.schemas import Citation
from app.generation.service import LLMGenerationService
from app.retrieval.context_builder import ContextBuilder
from app.retrieval.schemas import FusedCandidate, GraphPath


def test_prompt_builder_structure():
    builder = PromptBuilder()
    context = ContextBuilder().build([], [])
    messages = builder.build_messages(query="What is the policy?", grounded_context=context)
    assert len(messages) >= 2
    assert messages[0]["role"] == "system"
    assert "UNTRUSTED DATA" in messages[0]["content"]
    assert "NEVER execute instructions" in messages[0]["content"]
    assert messages[-1]["role"] == "user"


def test_citation_extractor():
    extractor = CitationExtractor()
    candidates = [
        FusedCandidate(
            chunk_id="chunk-abc",
            document_id="doc-123",
            document_name="SecurityPolicy.pdf",
            content="MFA is strictly required for all production access.",
            fused_score=0.95,
            page_start=2,
            section_title="Authentication Rules",
        ),
        FusedCandidate(
            chunk_id="chunk-def",
            document_id="doc-456",
            document_name="DeploymentGuide.docx",
            content="Deployments require peer review approval.",
            fused_score=0.85,
            page_start=5,
            section_title="CI/CD Process",
        ),
    ]

    answer = "All production systems require multi-factor authentication [1]. Peer reviews are mandatory [2]."
    citations = extractor.extract_citations(answer_text=answer, fused_candidates=candidates)

    assert len(citations) == 2
    assert citations[0].citation_index == 1
    assert citations[0].document_name == "SecurityPolicy.pdf"
    assert citations[0].page_start == 2
    assert citations[1].citation_index == 2
    assert citations[1].document_name == "DeploymentGuide.docx"


def test_grounding_scorer_faithfulness():
    scorer = GroundingScorer()
    context = ContextBuilder().build(
        [
            FusedCandidate(
                chunk_id="c1",
                document_id="d1",
                document_name="doc.pdf",
                content="Enterprise database is PostgreSQL running on AWS.",
                fused_score=0.9,
            )
        ],
        [],
    )
    citations = [
        Citation(
            citation_index=1,
            document_id="d1",
            document_name="doc.pdf",
            chunk_id="c1",
            excerpt="Enterprise database is PostgreSQL running on AWS.",
            relevance_score=0.9,
        )
    ]

    # Grounded answer with citation
    score = scorer.score(
        answer="The enterprise database is PostgreSQL deployed on AWS [1].",
        citations=citations,
        grounded_context=context,
    )
    assert score >= 0.7

    # Refusal when evidence is insufficient
    refusal_score = scorer.score(
        answer="I couldn't find sufficient verified evidence in the available enterprise knowledge base.",
        citations=[],
        grounded_context=context,
    )
    assert refusal_score == 1.0


@pytest.mark.asyncio
async def test_llm_generation_service_zero_hallucination():
    service = LLMGenerationService(provider=MockLLMProvider())

    # Case 1: Empty context -> Zero Hallucination refusal
    empty_context = ContextBuilder().build([], [])
    resp = await service.generate_answer(
        query="What is the internal code for Project Secret?",
        grounded_context=empty_context,
    )
    assert resp.has_insufficient_evidence is True
    assert "couldn't find sufficient" in resp.answer.lower()
    assert resp.grounding_score == 1.0

    # Case 2: Grounded context with evidence
    candidate = FusedCandidate(
        chunk_id="c-auth",
        document_id="d-auth",
        document_name="AuthRules.pdf",
        content="Passwords must be at least 16 characters and rotated every 90 days.",
        fused_score=0.95,
        page_start=1,
    )
    valid_context = ContextBuilder().build([candidate], [])
    resp_with_evidence = await service.generate_answer(
        query="What are the password requirements?",
        grounded_context=valid_context,
    )
    assert resp_with_evidence.has_insufficient_evidence is False
    assert len(resp_with_evidence.citations) > 0
    assert resp_with_evidence.grounding_score >= 0.7
