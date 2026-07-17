"""
Grayn AEO — Perplexity Provider

Queries Perplexity API using the OpenAI-compatible client
and returns the response with token-cost tracking.
"""

from openai import AsyncOpenAI
from app.config import get_settings
from app.models.schemas import EngineType
from app.services.providers.base import BaseProvider, EngineResult


class PerplexityProvider(BaseProvider):
    engine = EngineType.PERPLEXITY

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai",
        )
        self.model = "sonar-pro"

    async def _query(self, prompt: str, location: str | None = None) -> EngineResult:
        try:
            system_content = (
                "You are a helpful assistant answering real customer "
                "questions. Include specific product/brand names and "
                "cite your sources with URLs where possible."
            )
            if location:
                system_content += f"\n\nSimulate a user searching from this location: {location}"

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_content,
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2, # Perplexity recommends low temp for factual accuracy
                max_tokens=1500,
            )

            raw_text = response.choices[0].message.content or ""

            # Estimate cost (sonar-pro: ~$3.00/1M input, ~$15.00/1M output + $5 per 1000 requests)
            # We'll just approximate the token cost.
            usage = response.usage
            cost = 0.005 # base search cost
            if usage:
                cost += (usage.prompt_tokens * 3.0 + usage.completion_tokens * 15.0) / 1_000_000

            # Extract native citations
            native_citations = None
            raw_citations = getattr(response, "citations", None)
            if not raw_citations and hasattr(response, "model_dump"):
                raw_citations = response.model_dump().get("citations")
            
            if isinstance(raw_citations, list):
                native_citations = [{"url": str(url)} for url in raw_citations]

            return EngineResult(
                engine=self.engine.value,
                raw_text=raw_text,
                cost_usd=round(cost, 6),
                native_citations=native_citations,
            )
        except Exception as e:
            settings = get_settings()
            if settings.USE_MOCK_PROVIDERS:
                print(f"Provider exception: {e}. Falling back to mock data.")
                return EngineResult(
                    engine=self.engine.value,
                    raw_text=f"A review of the landscape for the requested topic reveals several competitive options. Users frequently point to robust feature sets and straightforward learning curves as deciding factors. While individual recommendations depend on exact needs, the top solutions consistently provide reliable and innovative tools.",
                    cost_usd=0.0,
                )
            raise e
