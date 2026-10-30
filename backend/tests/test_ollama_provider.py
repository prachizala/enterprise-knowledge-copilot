"""Unit tests for OllamaLLMProvider and local offline inference."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.core.config import settings
from app.generation.factory import get_llm_provider, set_llm_provider
from app.generation.ollama_provider import OllamaLLMProvider


def test_ollama_provider_properties():
    provider = OllamaLLMProvider(base_url="http://localhost:11434", model_name="llama3.2")
    assert provider.name == "ollama"
    assert provider.model_name == "llama3.2"
    assert provider.base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_ollama_provider_generate_success():
    provider = OllamaLLMProvider(base_url="http://localhost:11434", model_name="llama3.2")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "message": {"role": "assistant", "content": "Zero-trust network architecture is mandatory [1]."}
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.generate(
            prompt="What is required?",
            system_instruction="Strict enterprise facts only.",
        )
        assert "Zero-trust network architecture is mandatory [1]." in result


@pytest.mark.asyncio
async def test_ollama_provider_connection_error_graceful():
    provider = OllamaLLMProvider(base_url="http://localhost:11434", model_name="llama3.2")

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        result = await provider.generate(
            prompt="What is required?",
            system_instruction="Strict enterprise facts only.",
        )
        assert "Ollama local service is not reachable" in result


@pytest.mark.asyncio
async def test_ollama_provider_stream_generate():
    provider = OllamaLLMProvider(base_url="http://localhost:11434", model_name="llama3.2")

    lines = [
        '{"message": {"content": "Zero-trust "}}\n',
        '{"message": {"content": "network "}}\n',
        '{"message": {"content": "mandate."}}\n',
    ]

    async def mock_aiter_lines():
        for line in lines:
            yield line

    mock_stream_resp = MagicMock()
    mock_stream_resp.raise_for_status = MagicMock()
    mock_stream_resp.aiter_lines = mock_aiter_lines

    class MockStreamContext:
        async def __aenter__(self):
            return mock_stream_resp

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient.stream", return_value=MockStreamContext()):
        collected = []
        async for chunk in provider.stream_generate(
            prompt="What is required?",
            system_instruction="Strict enterprise facts only.",
        ):
            collected.append(chunk)

        assert "".join(collected) == "Zero-trust network mandate."


def test_factory_resolves_ollama():
    set_llm_provider(None)
    with patch.object(settings, "LLM_PROVIDER", "ollama"):
        with patch.object(settings, "OLLAMA_MODEL", "qwen2.5"):
            provider = get_llm_provider()
            assert isinstance(provider, OllamaLLMProvider)
            assert provider.model_name == "qwen2.5"
    set_llm_provider(None)
