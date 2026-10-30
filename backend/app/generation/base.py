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
        prompt: str = "",
        system_instruction: str = "",
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
        if isinstance(text, tuple):
            text = text[0]
        words = str(text).split(" ")
        for i, w in enumerate(words):
            yield w + (" " if i < len(words) - 1 else "")

    async def stream(
        self,
        prompt: str = "",
        system_instruction: str = "",
        messages: list = None,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        **kwargs,
    ):
        """Standardized streaming method supporting prompt or chat messages."""
        if messages:
            if not prompt:
                prompt = "\n".join(m.get("content", "") for m in messages if m.get("role") == "user")
            if not system_instruction:
                system_instruction = "\n".join(m.get("content", "") for m in messages if m.get("role") == "system")

        async for chunk in self.stream_generate(
            prompt=prompt,
            system_instruction=system_instruction,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        ):
            yield chunk
