"""Relationship extraction providers: Mock (deterministic) and OpenAI LLM."""

import asyncio
import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.extraction.relationships.base import (
    RelationshipExtractionError,
    RelationshipExtractionProvider,
    RelationshipExtractionTimeoutError,
)
from app.extraction.relationships.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


# ── Deterministic Mock Provider ──────────────────────────────────────────────

class MockRelationshipExtractionProvider(RelationshipExtractionProvider):
    """Deterministic mock provider for testing and offline development.

    Inspects the supplied entities and pairs them up based on typed enterprise
    heuristics and keyword matching in chunk_text. Always uses only the provided
    entities.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-v1"

    async def extract_relationships(
        self,
        chunk_text: str,
        entities: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Deterministically extract relationships between supplied entity pairs."""
        if len(entities) < 2:
            return []

        lower_text = chunk_text.lower()
        relationships: List[Dict[str, Any]] = []

        # Find first sentence or passage as default evidence
        sentences = [s.strip() for s in re.split(r"[.!?\n]", chunk_text) if len(s.strip()) > 10]
        default_evidence = sentences[0] if sentences else chunk_text[:120].strip()

        # Iterate over distinct pairs of entities
        for i in range(len(entities)):
            for j in range(i + 1, min(len(entities), i + 4)):
                e1 = entities[i]
                e2 = entities[j]

                t1 = e1.get("entity_type", "OTHER")
                t2 = e2.get("entity_type", "OTHER")
                alias1 = e1.get("alias_id", f"E{i+1}")
                alias2 = e2.get("alias_id", f"E{j+1}")

                rel_type: Optional[str] = None
                source_alias = alias1
                target_alias = alias2
                confidence = 0.88

                # Typed enterprise heuristics
                if t1 == "PERSON" and t2 == "ORGANIZATION":
                    rel_type = "WORKS_FOR"
                    source_alias, target_alias = alias1, alias2
                elif t1 == "ORGANIZATION" and t2 == "PERSON":
                    rel_type = "WORKS_FOR"
                    source_alias, target_alias = alias2, alias1
                elif t1 == "PERSON" and t2 == "DEPARTMENT":
                    if any(w in lower_text for w in ["manage", "lead", "head"]):
                        rel_type = "MANAGES"
                    else:
                        rel_type = "MEMBER_OF"
                elif t1 == "PERSON" and t2 == "PERSON":
                    if any(w in lower_text for w in ["report", "under", "supervise"]):
                        rel_type = "REPORTS_TO"
                    else:
                        rel_type = "RELATED_TO"
                elif (t1 in ["ORGANIZATION", "DEPARTMENT"]) and t2 == "PROJECT":
                    rel_type = "OWNS"
                elif t1 == "PROJECT" and (t2 in ["ORGANIZATION", "DEPARTMENT"]):
                    rel_type = "OWNS"
                    source_alias, target_alias = alias2, alias1
                elif t1 == "PROJECT" and t2 == "TECHNOLOGY":
                    rel_type = "USES"
                elif t1 == "TECHNOLOGY" and t2 == "PROJECT":
                    rel_type = "USES"
                    source_alias, target_alias = alias2, alias1
                elif t1 in ["ORGANIZATION", "DEPARTMENT"] and t2 == "LOCATION":
                    rel_type = "LOCATED_IN"
                elif t1 == "POLICY" and t2 in ["ORGANIZATION", "DEPARTMENT", "PROJECT"]:
                    rel_type = "APPLIES_TO"
                elif t1 in ["ORGANIZATION", "DEPARTMENT", "PROJECT"] and t2 == "POLICY":
                    rel_type = "APPLIES_TO"
                    source_alias, target_alias = alias2, alias1
                else:
                    # Generic related fallback for adjacent co-occurring entities
                    rel_type = "RELATED_TO"
                    confidence = 0.75

                # Find specific sentence mentioning either entity if possible
                n1 = (e1.get("mention_text") or e1.get("display_name", "")).lower()
                n2 = (e2.get("mention_text") or e2.get("display_name", "")).lower()
                evidence = default_evidence
                for s in sentences:
                    s_lower = s.lower()
                    if (n1 and n1 in s_lower) or (n2 and n2 in s_lower):
                        evidence = s
                        break

                relationships.append({
                    "source_entity": source_alias,
                    "relationship_type": rel_type,
                    "target_entity": target_alias,
                    "confidence": confidence,
                    "evidence_text": evidence,
                })

        return relationships


# ── OpenAI LLM Provider ──────────────────────────────────────────────────────

class LLMRelationshipExtractionProvider(RelationshipExtractionProvider):
    """OpenAI chat completions-based relationship extractor using JSON mode.

    Security: Never logs chunk text, raw prompt, or complete LLM completions.
    """

    def __init__(self, api_key: str, model: str, timeout_seconds: int, max_retries: int) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract_relationships(
        self,
        chunk_text: str,
        entities: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Call OpenAI chat completion with structured JSON output."""
        if len(entities) < 2:
            return []

        try:
            from openai import AsyncOpenAI, APIError, APITimeoutError
        except ImportError as exc:
            raise RelationshipExtractionError("openai package not installed") from exc

        client = AsyncOpenAI(api_key=self._api_key, timeout=float(self._timeout))
        context = metadata.get("section_header", "")
        user_message = build_user_prompt(chunk_text, entities, context=context)

        last_exc: Exception = Exception("No attempts made")
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                raw = response.choices[0].message.content or "{}"
                parsed = json.loads(raw)

                # Look for "relationships" list
                if isinstance(parsed, dict) and "relationships" in parsed:
                    items = parsed["relationships"]
                elif isinstance(parsed, list):
                    items = parsed
                else:
                    # Find first list value if wrapped in another key
                    items = []
                    for val in parsed.values():
                        if isinstance(val, list):
                            items = val
                            break

                logger.debug(
                    "LLM relationship extraction returned %d items (attempt %d/%d)",
                    len(items),
                    attempt,
                    self._max_retries,
                )
                return items

            except APITimeoutError as exc:
                last_exc = exc
                logger.warning(
                    "LLM relationship extraction timeout (attempt %d/%d)",
                    attempt,
                    self._max_retries,
                )
                if attempt == self._max_retries:
                    raise RelationshipExtractionTimeoutError(
                        f"Relationship extraction timed out after {self._max_retries} attempts"
                    ) from exc
                await asyncio.sleep(2 ** attempt)

            except APIError as exc:
                last_exc = exc
                logger.warning(
                    "LLM relationship extraction API error (attempt %d/%d): %s",
                    attempt,
                    self._max_retries,
                    type(exc).__name__,
                )
                if attempt == self._max_retries:
                    raise RelationshipExtractionError(
                        f"LLM relationship extraction failed: {type(exc).__name__}"
                    ) from exc
                await asyncio.sleep(2 ** attempt)

            except (json.JSONDecodeError, ValueError) as exc:
                last_exc = exc
                logger.warning(
                    "LLM relationship extraction parse error (attempt %d/%d)",
                    attempt,
                    self._max_retries,
                )
                if attempt == self._max_retries:
                    raise RelationshipExtractionError("Failed to parse LLM extraction response") from exc
                await asyncio.sleep(1)

        raise RelationshipExtractionError("LLM relationship extraction failed after retries") from last_exc


# ── Provider Factory & Singleton ─────────────────────────────────────────────

_provider_singleton: Optional[RelationshipExtractionProvider] = None


def get_relationship_extraction_provider() -> RelationshipExtractionProvider:
    """Return configured relationship extraction provider with graceful mock fallback."""
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton

    from app.core.config import settings

    provider_name = (settings.RELATIONSHIP_EXTRACTION_PROVIDER or "").strip().lower()
    api_key = (settings.OPENAI_API_KEY or settings.EMBEDDING_API_KEY or "").strip()

    if provider_name == "openai" and api_key:
        try:
            _provider_singleton = LLMRelationshipExtractionProvider(
                api_key=api_key,
                model=settings.RELATIONSHIP_EXTRACTION_MODEL,
                timeout_seconds=settings.RELATIONSHIP_EXTRACTION_TIMEOUT_SECONDS,
                max_retries=settings.RELATIONSHIP_EXTRACTION_MAX_RETRIES,
            )
            logger.info(
                "Relationship extraction: using OpenAI provider with model %s",
                settings.RELATIONSHIP_EXTRACTION_MODEL,
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize LLM relationship provider (%s). Falling back to mock.",
                exc,
            )
            _provider_singleton = MockRelationshipExtractionProvider()
    else:
        _provider_singleton = MockRelationshipExtractionProvider()
        if provider_name:
            logger.warning(
                "Relationship provider '%s' configured but no API key found. Using mock.",
                provider_name,
            )
        else:
            logger.debug("No relationship provider configured. Using mock.")

    return _provider_singleton


def set_relationship_extraction_provider(
    provider: Optional[RelationshipExtractionProvider],
) -> None:
    """Override singleton provider for testing."""
    global _provider_singleton
    _provider_singleton = provider
