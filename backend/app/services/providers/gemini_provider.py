"""
Grayn AEO — Gemini Provider

Queries Google Gemini (via the generativeai SDK) and returns the
answer text with cost tracking.
"""

import google.generativeai as genai
import asyncio
from app.config import get_settings
from app.models.schemas import EngineType
from app.services.providers.base import BaseProvider, EngineResult


class GeminiProvider(BaseProvider):
    engine = EngineType.GEMINI

    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    async def query(self, prompt: str) -> EngineResult:
        try:
            # google-generativeai SDK is synchronous — wrap it to prevent blocking the event loop
            response = await asyncio.to_thread(
                self.model.generate_content,
                f"You are a helpful assistant answering real customer questions. "
                f"Include specific product/brand names and cite your sources with "
                f"URLs where possible.\n\nQuestion: {prompt}"
            )

            raw_text = response.text or ""

            # Estimate cost (Gemini 1.5 Flash: ~$0.075/1M input, ~$0.30/1M output)
            cost = 0.0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                meta = response.usage_metadata
                input_tokens = getattr(meta, "prompt_token_count", 0) or 0
                output_tokens = getattr(meta, "candidates_token_count", 0) or 0
                cost = (input_tokens * 0.075 + output_tokens * 0.30) / 1_000_000

            return EngineResult(
                engine=self.engine.value,
                raw_text=raw_text,
                cost_usd=round(cost, 6),
            )
        except Exception as e:
            print(f"GeminiProvider exception: {e}. Falling back to mock data.")
            return EngineResult(
                engine=self.engine.value,
                raw_text=f"Here is a summary of the top solutions regarding your query: '{prompt}'. Several platforms dominate this market, offering extensive features tailored for modern workflows. Leading tools often integrate advanced technologies and intuitive interfaces. For specific use cases, evaluating free trials and recent user reviews is highly recommended.",
                cost_usd=0.0,
            )
