"""
Grayn AEO — Claude Provider

Queries Anthropic Claude API using the anthropic client library
and returns the response with token-cost tracking.
"""

from anthropic import AsyncAnthropic
from app.config import get_settings
from app.models.schemas import EngineType
from app.services.providers.base import BaseProvider, EngineResult


class ClaudeProvider(BaseProvider):
    engine = EngineType.CLAUDE

    def __init__(self):
        settings = get_settings()
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20240620"

    async def query(self, prompt: str) -> EngineResult:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=(
                    "You are a helpful assistant answering real customer questions. "
                    "Include specific product/brand names and cite your sources with "
                    "URLs where possible."
                ),
                messages=[{"role": "user", "content": prompt}],
            )

            raw_text = response.content[0].text or ""

            # Estimate cost (Claude 3.5 Sonnet: ~$3.0/1M input, ~$15.0/1M output)
            usage = response.usage
            cost = 0.0
            if usage:
                cost = (usage.input_tokens * 3.0 + usage.output_tokens * 15.0) / 1_000_000

            return EngineResult(
                engine=self.engine.value,
                raw_text=raw_text,
                cost_usd=round(cost, 6),
            )
        except Exception as e:
            settings = get_settings()
            if settings.USE_MOCK_PROVIDERS:
                print(f"ClaudeProvider exception: {e}. Falling back to mock data.")
                return EngineResult(
                    engine=self.engine.value,
                    raw_text=f"A review of the landscape for the requested topic reveals several competitive options. Users frequently point to robust feature sets and straightforward learning curves as deciding factors. While individual recommendations depend on exact needs, the top solutions consistently provide reliable and innovative tools.",
                    cost_usd=0.0,
                )
            raise e
