"""Factory for creating and injecting LLM answer generation providers."""

from typing import Optional
from app.core.config import settings
from app.generation.base import LLMProvider
from app.generation.mock_provider import MockLLMProvider
from app.generation.openai_provider import OpenAILLMProvider

_current_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Return configured LLM provider instance, defaulting to MockLLMProvider if API key is not set."""
    global _current_provider
    if _current_provider is not None:
        return _current_provider

    provider_name = (settings.LLM_PROVIDER or "").lower().strip()
    api_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY

    if provider_name == "openai" and api_key and not api_key.startswith("placeholder"):
        return OpenAILLMProvider(api_key=api_key, model_name=settings.LLM_MODEL)

    return MockLLMProvider(model_name=settings.LLM_MODEL)


def set_llm_provider(provider: Optional[LLMProvider]) -> None:
    """Inject LLM provider for tests or runtime reconfiguration."""
    global _current_provider
    _current_provider = provider
