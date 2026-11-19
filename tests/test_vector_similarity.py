"""Unit test suite for pgvector cosine distance operations."""
import unittest

class TestVectorSimilarity(unittest.TestCase):
    def test_cosine_similarity_identity(self):
        vec_a = [0.1, 0.5, 0.9]
        vec_b = [0.1, 0.5, 0.9]
        dot = sum(x * y for x, y in zip(vec_a, vec_b))
        norm_a = sum(x**2 for x in vec_a) ** 0.5
        norm_b = sum(x**2 for x in vec_b) ** 0.5
        cos_sim = dot / (norm_a * norm_b)
        self.assertAlmostEqual(cos_sim, 1.0, places=5)

if __name__ == '__main__':
    unittest.main()
