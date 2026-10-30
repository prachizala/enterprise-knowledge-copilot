"""Deterministic mock entity extraction provider for testing and development.

Returns a fixed set of entities derived from the input text so tests do not
require any API key or network connection. The output is deterministic for
the same input, making tests reproducible.
"""

import hashlib
import re
from typing import Any, Dict, List

from app.extraction.entities.base import EntityExtractionProvider
from app.extraction.entities.registry import ENTITY_TYPES_SORTED

# Fixed entity templates reused for all mock extraction calls
_MOCK_ENTITIES_TEMPLATE = [
    {"text": "Acme Corporation", "type": "ORGANIZATION", "normalized_name": "acme corporation", "confidence": 0.95},
    {"text": "John Smith", "type": "PERSON", "normalized_name": "john smith", "confidence": 0.92},
    {"text": "Engineering Department", "type": "DEPARTMENT", "normalized_name": "engineering department", "confidence": 0.88},
    {"text": "Project Atlas", "type": "PROJECT", "normalized_name": "project atlas", "confidence": 0.85},
    {"text": "Python", "type": "TECHNOLOGY", "normalized_name": "python", "confidence": 0.90},
    {"text": "New York", "type": "LOCATION", "normalized_name": "new york", "confidence": 0.91},
    {"text": "Security Policy v2", "type": "POLICY", "normalized_name": "security policy v2", "confidence": 0.87},
    {"text": "Senior Engineer", "type": "ROLE", "normalized_name": "senior engineer", "confidence": 0.83},
]


def _normalize_name(text: str) -> str:
    """Apply conservative normalization: lowercase, trim, collapse spaces."""
    return re.sub(r"\s+", " ", text.strip().lower())


class MockEntityExtractionProvider(EntityExtractionProvider):
    """Mock provider that returns a deterministic subset of preset entities.

    The number of returned entities is derived from a hash of the input text
    so different chunks produce slightly different results while remaining
    fully deterministic and reproducible.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-v1"

    async def extract_entities(
        self,
        text: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Return a deterministic subset of mock entities based on text hash."""
        # Derive a stable count 2–5 from text hash
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        count = (digest[0] % 4) + 2  # 2 to 5

        selected = _MOCK_ENTITIES_TEMPLATE[:count]
        results = []
        for ent in selected:
            results.append({
                "text": ent["text"],
                "type": ent["type"],
                "normalized_name": ent["normalized_name"],
                "confidence": ent["confidence"],
                "start_char": None,
                "end_char": None,
            })
        return results
