"""
Grayn AEO — Groq Provider

Queries Groq's LPU completions API using the OpenAI-compatible client
and returns the response with token-cost tracking.
"""

from openai import AsyncOpenAI
from app.config import get_settings
from app.models.schemas import EngineType
from app.services.providers.base import BaseProvider, EngineResult


class GroqProvider(BaseProvider):
    engine = EngineType.GROQ

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = "llama-3.3-70b-versatile"

    async def _query(self, prompt: str, location: str | None = None) -> EngineResult:
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
            temperature=0.7,
            max_tokens=1500,
        )

        raw_text = response.choices[0].message.content or ""

        # Estimate cost (Llama-3-70b on Groq: ~$0.59/1M input, ~$0.79/1M output)
        usage = response.usage
        cost = 0.0
        if usage:
            cost = (usage.prompt_tokens * 0.59 + usage.completion_tokens * 0.79) / 1_000_000

        return EngineResult(
            engine=self.engine.value,
            raw_text=raw_text,
            cost_usd=round(cost, 6),
        )
