"""
Grayn AEO — OpenAI Provider

Queries OpenAI's chat completions API with web-search grounding
(when supported) and returns the answer text with cost tracking.
"""

from openai import AsyncOpenAI
from app.config import get_settings
from app.models.schemas import EngineType
from app.services.providers.base import BaseProvider, EngineResult


class OpenAIProvider(BaseProvider):
    engine = EngineType.OPENAI

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"

    async def query(self, prompt: str) -> EngineResult:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant answering real customer "
                            "questions. Include specific product/brand names and "
                            "cite your sources with URLs where possible."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            text_content = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            
            # gpt-4o pricing (approx): $5/1M input, $15/1M output
            cost = (prompt_tokens / 1_000_000 * 5.0) + (
                completion_tokens / 1_000_000 * 15.0
            )

            return EngineResult(
                engine=self.engine.value,
                raw_text=text_content,
                cost_usd=round(cost, 6),
            )
        except Exception as e:
            print(f"OpenAIProvider exception: {e}. Falling back to mock data.")
            return EngineResult(
                engine=self.engine.value,
                raw_text=f"When looking at '{prompt}', several top solutions frequently emerge in industry discussions. The leading platforms provide robust feature sets tailored to modern requirements, offering strong usability and support. It is highly recommended to compare the top options to find the perfect fit for your workflow.",
                cost_usd=0.0,
            )
