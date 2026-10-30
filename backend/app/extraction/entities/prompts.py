"""Prompt templates for LLM-based entity extraction."""

from app.extraction.entities.registry import ENTITY_TYPES_SORTED

# Build the entity type list once at module load
_TYPES_LIST = "\n".join(f"  - {t}" for t in ENTITY_TYPES_SORTED)

SYSTEM_PROMPT = f"""You are an enterprise knowledge extraction system.
Extract named entities from the provided text chunk.

Return a JSON array where each object has these fields:
- "text": exact surface form from the source text (string, required)
- "type": one of the allowed types (string, required)
- "normalized_name": canonical name for deduplication, lowercase, trimmed (string, required)
- "confidence": float between 0.0 and 1.0 (required)
- "start_char": character offset where entity starts (integer or null)
- "end_char": character offset where entity ends, exclusive (integer or null)

Allowed entity types:
{_TYPES_LIST}

Rules:
- Only extract entities clearly present in the text.
- Do not invent or hallucinate entities.
- Return [] if no entities are found.
- Map unrecognized types to "OTHER".
- normalized_name must be lowercase, trimmed, with consecutive spaces collapsed.
- Do not include PII beyond what is explicitly in the provided text.
- Return raw JSON array only; no markdown, no explanation.
"""


def build_user_prompt(text: str, context: str = "") -> str:
    """Build the user message for entity extraction.

    Args:
        text: The chunk text to analyze.
        context: Optional context hint (e.g. section header) for the LLM.

    Returns:
        Formatted user prompt string.
    """
    parts = []
    if context:
        parts.append(f"Context: {context}\n")
    parts.append(f"Text:\n{text}")
    return "\n".join(parts)
