"""
Grayn AEO — Grok Provider (xAI)

Connects to the xAI Grok API.
Uses the OpenAI-compatible python client with custom base URL.
"""

import time
from openai import AsyncOpenAI
from app.config import get_settings
from app.services.providers.base import BaseProvider, EngineResult


class GrokProvider(BaseProvider):
    def __init__(self):
        settings = get_settings()
        self.engine = "grok"
        self.client = AsyncOpenAI(
            api_key=settings.GROK_API_KEY,
            base_url="https://api.xai.com/v1"
        )
        self.model = "grok-beta"

    async def query(self, prompt: str) -> EngineResult:
        try:
            messages = [{"role": "user", "content": prompt}]

            # Timing to simulate standard engine latency capturing
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
            )
            
            raw_text = response.choices[0].message.content

            # xAI pricing: grok-beta is ~ $5.00 / 1M input, $15.00 / 1M output
            # (Using approximate/mock pricing structure for tracking)
            in_tokens = response.usage.prompt_tokens
            out_tokens = response.usage.completion_tokens
            cost = (in_tokens / 1_000_000) * 5.00 + (out_tokens / 1_000_000) * 15.00

            return EngineResult(
                engine=self.engine,
                raw_text=raw_text,
                cost_usd=cost,
            )        except Exception as e:
            from app.config import get_settings
            settings = get_settings()
            if settings.USE_MOCK_PROVIDERS:
                print(f"Provider exception: {e}. Falling back to mock data.")
            return EngineResult(
                engine=self.engine,
                raw_text=f"The top results regarding the requested topic highlight a competitive market of platforms. These leading options are widely recognized for their comprehensive feature sets and ease of use. Analysts suggest evaluating these top-tier solutions based on specific pricing and workflow needs.",
                cost_usd=0.0,
            )
            raise e
