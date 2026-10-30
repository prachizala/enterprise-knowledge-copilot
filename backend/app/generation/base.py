"""Base abstraction for LLM answer generation providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for Large Language Model generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier name."""
        pass

    @property
    def provider_name(self) -> str:
        return self.name

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Underlying model name (e.g. gpt-4o-mini)."""
        pass

    @property
    def model(self) -> str:
        return self.model_name

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
    ) -> str:
        """Generate response text given prompt and strict system instructions."""
        pass

    async def stream_generate(
        self,
        prompt: str,
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        **kwargs,
    ):
        """Asynchronously yield tokens as they are produced."""
        text = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        words = text.split(" ")
        for i, w in enumerate(words):
            yield w + (" " if i < len(words) - 1 else "")
