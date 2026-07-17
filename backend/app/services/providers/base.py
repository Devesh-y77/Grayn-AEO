"""
Grayn AEO — Base Provider Interface

All AI engine providers (OpenAI, Gemini, Perplexity, Mock) implement
this abstract class.  The factory function ``get_provider()`` returns
the correct implementation based on the current configuration.
"""

from abc import ABC, abstractmethod
from app.models.schemas import EngineType


class EngineResult:
    """Uniform result from any engine provider."""

    def __init__(self, engine: str, raw_text: str, cost_usd: float = 0.0, native_citations: list[dict] | None = None):
        self.engine = engine
        self.raw_text = raw_text
        self.cost_usd = cost_usd
        self.native_citations = native_citations


import asyncio
import os
from typing import Dict
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception

# Global semaphores per engine
_engine_semaphores: Dict[EngineType, asyncio.Semaphore] = {}

def get_semaphore(engine: EngineType) -> asyncio.Semaphore:
    if engine not in _engine_semaphores:
        env_name = f"{engine.name}_MAX_CONCURRENCY"
        limit = int(os.environ.get(env_name, 5))
        _engine_semaphores[engine] = asyncio.Semaphore(limit)
    return _engine_semaphores[engine]

def is_retryable_exception(e: Exception) -> bool:
    # Always retry timeouts
    if isinstance(e, (asyncio.TimeoutError, TimeoutError)):
        return True
        
    # Check specific SDK exceptions
    type_name = type(e).__name__
    if type_name in ("RateLimitError", "InternalServerError", "APITimeoutError"):
        return True
        
    # For httpx/aiohttp errors with status_code
    status_code = getattr(e, "status_code", getattr(e, "status", None))
    if status_code is not None:
        try:
            code = int(status_code)
            return code == 429 or code >= 500
        except (ValueError, TypeError):
            pass
            
    # For standard HTTPError types in various libraries (requests, urllib)
    response = getattr(e, "response", None)
    if response is not None and hasattr(response, "status_code"):
        try:
            code = int(response.status_code)
            return code == 429 or code >= 500
        except (ValueError, TypeError):
            pass
            
    return False

class BaseProvider(ABC):
    """Abstract base for all answer-engine providers."""

    engine: EngineType

    async def query(self, prompt: str, location: str | None = None) -> EngineResult:
        """Send a prompt and return the engine's answer with resilience wrappers."""
        sem = get_semaphore(self.engine)
        
        @retry(
            wait=wait_random_exponential(multiplier=2, max=10),
            stop=stop_after_attempt(3),
            retry=retry_if_exception(is_retryable_exception),
            reraise=True
        )
        async def _run_with_retry():
            async with sem:
                async with asyncio.timeout(90.0):
                    return await self._query(prompt, location)
                    
        return await _run_with_retry()

    @abstractmethod
    async def _query(self, prompt: str, location: str | None = None) -> EngineResult:
        """Internal method to be implemented by providers."""
        ...


def get_provider(engine: EngineType) -> BaseProvider:
    """
    Factory: return the correct provider for the given engine.

    Automatically falls back to mock if the real provider's API key
    is not configured.
    """
    from app.config import get_settings

    settings = get_settings()

    if engine == EngineType.OPENAI:
        if settings.openai_available:
            from app.services.providers.openai_provider import OpenAIProvider
            return OpenAIProvider()
        if settings.USE_MOCK_PROVIDERS:
            from app.services.providers.mock_provider import MockProvider
            return MockProvider(engine)
        raise ValueError(f"OPENAI_API_KEY is missing for engine {engine.value}")

    if engine == EngineType.GEMINI:
        if settings.gemini_available:
            from app.services.providers.gemini_provider import GeminiProvider
            return GeminiProvider()
        if settings.USE_MOCK_PROVIDERS:
            from app.services.providers.mock_provider import MockProvider
            return MockProvider(engine)
        raise ValueError(f"GEMINI_API_KEY is missing for engine {engine.value}")

    if engine == EngineType.GOOGLE_AI:
        from app.services.providers.browser_provider import BrowserProvider
        return BrowserProvider(engine)

    if engine == EngineType.PERPLEXITY:
        if settings.perplexity_available:
            from app.services.providers.perplexity_provider import PerplexityProvider
            return PerplexityProvider()
        if settings.USE_MOCK_PROVIDERS:
            from app.services.providers.mock_provider import MockProvider
            return MockProvider(engine)
        raise ValueError(f"PERPLEXITY_API_KEY is missing for engine {engine.value}")
    if engine == EngineType.CLAUDE:
        if settings.anthropic_available:
            from app.services.providers.claude_provider import ClaudeProvider
            return ClaudeProvider()
        if settings.USE_MOCK_PROVIDERS:
            from app.services.providers.mock_provider import MockProvider
            return MockProvider(engine)
        raise ValueError(f"ANTHROPIC_API_KEY is missing for engine {engine.value}")

    if engine == EngineType.DEEPSEEK:
        if settings.deepseek_available:
            from app.services.providers.deepseek_provider import DeepSeekProvider
            return DeepSeekProvider()
        if settings.USE_MOCK_PROVIDERS:
            from app.services.providers.mock_provider import MockProvider
            return MockProvider(engine)
        raise ValueError(f"DEEPSEEK_API_KEY is missing for engine {engine.value}")

    if engine == EngineType.GROQ:
        if settings.groq_available:
            from app.services.providers.groq_provider import GroqProvider
            return GroqProvider()
        if settings.USE_MOCK_PROVIDERS:
            from app.services.providers.mock_provider import MockProvider
            return MockProvider(engine)
        raise ValueError(f"GROQ_API_KEY is missing for engine {engine.value}")
        
    if engine == EngineType.GROK:
        if settings.grok_available:
            from app.services.providers.grok_provider import GrokProvider
            return GrokProvider()
        if settings.USE_MOCK_PROVIDERS:
            from app.services.providers.mock_provider import MockProvider
            return MockProvider(engine)
        raise ValueError(f"GROK_API_KEY is missing for engine {engine.value}")

    raise ValueError(f"Unknown engine: {engine}")
