"""Embedding vector cache with SHA-256 key hashing to prevent redundant LLM inference."""

import hashlib


class EmbeddingCache:
    """LRU-style in-memory cache for dense embedding query vectors."""

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.cache = {}

    @staticmethod
    def compute_hash(query_text: str) -> str:
        """Returns deterministic SHA-256 fingerprint of query text."""
        return hashlib.sha256(query_text.strip().lower().encode('utf-8')).hexdigest()

    def get(self, query_text: str) -> list[float] | None:
        """Retrieves cached embedding vector if present."""
        return self.cache.get(self.compute_hash(query_text))

    def put(self, query_text: str, vector: list[float]):
        """Caches embedding vector while enforcing maximum cache capacity."""
        if len(self.cache) >= self.max_entries:
            # Evict oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[self.compute_hash(query_text)] = vector
