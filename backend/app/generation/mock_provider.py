"""Deterministic, offline-capable Mock LLM provider for local development, zero-cost operations, and tests."""

import re
from app.generation.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Synthesizes grounded enterprise answers strictly referencing prompt excerpts and graph facts."""

    def __init__(self, model_name: str = "mock-gpt-4o-mini") -> None:
        self._model = model_name

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str = "",
        system_instruction: str = "",
        messages: list = None,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        **kwargs,
    ) -> str:
        if messages:
            if not prompt:
                prompt = "\n".join(m.get("content", "") for m in messages if m.get("role") == "user")
            if not system_instruction:
                system_instruction = "\n".join(m.get("content", "") for m in messages if m.get("role") == "system")

        prompt = prompt or ""
        # Check if prompt contains document excerpts or graph paths
        has_excerpts = "<<<DOCUMENT_EXCERPT:" in prompt
        has_paths = "=== VERIFIED KNOWLEDGE GRAPH PATHS ===" in prompt

        if not has_excerpts and not has_paths:
            return "I couldn't find sufficient evidence in the available enterprise knowledge base to answer this reliably."

        # Extract question from prompt
        q_match = re.search(r"USER QUESTION:\s*(.+?)(?:\n|$)", prompt, re.IGNORECASE)
        question = q_match.group(1).strip() if q_match else "the enterprise inquiry"

        # Extract graph paths if present
        paths_found = []
        if has_paths:
            path_lines = re.findall(r"\[\d+\]\s+([^\n\[]+)", prompt)
            paths_found = [p.strip() for p in path_lines if p.strip()]

        # Extract text sentences from document excerpts
        excerpt_texts = re.findall(r"<<<DOCUMENT_EXCERPT:[^>]*>>>\s*(.+?)\s*<<<END_DOCUMENT_EXCERPT>>>", prompt, re.DOTALL)

        answer_parts = []

        if paths_found:
            primary_path = paths_found[0]
            answer_parts.append(
                f"Based on the enterprise knowledge graph and verified documentation, {primary_path} [1]."
            )
            if len(paths_found) > 1:
                answer_parts.append(
                    f"Furthermore, multi-hop relationship traversal confirms that {paths_found[1]} [1]."
                )

        if excerpt_texts:
            # Use the first 1-2 excerpts
            first_snippet = excerpt_texts[0].strip()
            # Clean newlines
            clean_snip = " ".join(first_snippet.split())
            if len(clean_snip) > 220:
                clean_snip = clean_snip[:217] + "..."

            if not paths_found:
                answer_parts.append(f"Based on enterprise documentation: {clean_snip} [1].")
            else:
                answer_parts.append(f"Corroborating source records indicate: {clean_snip} [1].")

            if len(excerpt_texts) > 1:
                second_snippet = " ".join(excerpt_texts[1].strip().split())
                if len(second_snippet) > 200:
                    second_snippet = second_snippet[:197] + "..."
                answer_parts.append(f"In addition, documentation specifies that {second_snippet} [2].")

        if not answer_parts:
            return "I couldn't find sufficient evidence in the available enterprise knowledge base to answer this reliably."

        return " ".join(answer_parts)
