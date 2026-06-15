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

    def __init__(self, engine: str, raw_text: str, cost_usd: float = 0.0):
        self.engine = engine
        self.raw_text = raw_text
        self.cost_usd = cost_usd


class BaseProvider(ABC):
    """Abstract base for all answer-engine providers."""

    engine: EngineType

    @abstractmethod
    async def query(self, prompt: str) -> EngineResult:
        """Send a prompt and return the engine's answer."""
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
        from app.services.providers.browser_provider import BrowserProvider
        return BrowserProvider(engine)
        
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
