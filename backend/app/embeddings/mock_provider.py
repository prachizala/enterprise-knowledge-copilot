"""Deterministic offline mock embedding provider for tests and local development."""

import hashlib
import math
import re
from typing import List

from app.embeddings.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline embedding provider generating normalized 1536D vectors."""

    def __init__(
        self,
        model_name: str = "mock-text-embedding-3-small",
        dimensions: int = 1536,
    ) -> None:
        self._model_name = model_name
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic normalized unit vector from input text."""
        if not text or not text.strip():
            # Uniform non-zero vector for empty strings
            val = 1.0 / math.sqrt(self._dimensions)
            return [val] * self._dimensions

        vec = [0.0] * self._dimensions

        # Token hashing for pseudo-semantic overlap
        words = re.findall(r"\w+", text.lower())
        for word in words:
            # Consistent 32-bit hash
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self._dimensions
            sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
            weight = 1.0 + 0.1 * (len(word) % 5)
            vec[idx] += sign * weight

        # Add deterministic dispersion from full string hash
        full_hash = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        for j in range(self._dimensions):
            # Seed pseudo-random perturbation
            pseudo_val = ((full_hash + (j * 7919)) % 1000 - 500) / 10000.0
            vec[j] += pseudo_val

        # L2 Normalize to unit vector (||v||_2 = 1.0)
        norm_sq = sum(x * x for x in vec)
        norm = math.sqrt(norm_sq) if norm_sq > 0.0 else 1.0
        return [float(x / norm) for x in vec]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate deterministic unit vectors for a list of texts."""
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        """Generate deterministic unit vector for a search query."""
        return self._generate_vector(query)
