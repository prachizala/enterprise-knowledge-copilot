"""Prompts for LLM-based enterprise relationship extraction."""

from typing import Any, Dict, List
from app.extraction.relationships.registry import RELATIONSHIP_TYPES_SORTED

# Formatted vocabulary list
_TYPES_LIST = "\n".join(f"  - {t}" for t in RELATIONSHIP_TYPES_SORTED)

SYSTEM_PROMPT = f"""You are an enterprise knowledge graph relationship extraction specialist.
Your mission is to extract factual, grounded relationships between the PROVIDED entities based SOLELY on the supplied text chunk.

RULES:
1. ONLY use entities from the provided ENTITIES list. Do NOT invent, assume, or hallucinate entities not in the list.
2. ONLY extract relationships explicitly supported and grounded in the text passage.
3. Do NOT use outside world knowledge or extrapolate beyond what is written.
4. ONLY use the allowed enterprise relationship types:
{_TYPES_LIST}
5. Assign a confidence score between 0.0 and 1.0.
6. Provide the exact or concise evidence sentence/phrase from the text in "evidence_text".
7. Explicit directionality matters:
   - "Alice works for Acme" -> source="Alice" (or its ID), type="WORKS_FOR", target="Acme" (or its ID)
   - "Alice reports to Bob" -> source="Alice", type="REPORTS_TO", target="Bob"
   - "Project Alpha uses PostgreSQL" -> source="Project Alpha", type="USES", target="PostgreSQL"
8. Never create self-referential relationships (source == target).
9. Output STRICT JSON format with a single top-level key "relationships" containing an array of objects:
{{
  "relationships": [
    {{
      "source_entity": "E1",
      "relationship_type": "WORKS_FOR",
      "target_entity": "E2",
      "confidence": 0.95,
      "evidence_text": "Alice works for Acme Corporation."
    }}
  ]
}}
If no relationships are supported by the text, return {{"relationships": []}}.
"""


def build_user_prompt(
    chunk_text: str,
    entities: List[Dict[str, Any]],
    context: str = "",
) -> str:
    """Format user message with chunk text and numbered entity references."""
    entity_lines = []
    for ent in entities:
        alias = ent.get("alias_id", "E?")
        name = ent.get("display_name") or ent.get("canonical_name", "")
        etype = ent.get("entity_type", "OTHER")
        mention = ent.get("mention_text", name)
        entity_lines.append(f"- {alias}: \"{name}\" (Type: {etype}, Mention: \"{mention}\")")

    entities_block = "\n".join(entity_lines)

    parts = []
    if context:
        parts.append(f"Section Context: {context}\n")

    parts.append(f"ENTITIES PRESENT IN THIS CHUNK:\n{entities_block}\n")
    parts.append(f"TEXT PASSAGE:\n{chunk_text}")

    return "\n".join(parts)
