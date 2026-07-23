"""
Grayn AEO — Google AI Overviews Provider

Simulates Google AI Overviews using the Gemini API.
"""

import google.generativeai as genai
from app.config import get_settings
from app.models.schemas import EngineType
from app.services.providers.base import BaseProvider, EngineResult


class GoogleAIProvider(BaseProvider):
    def __init__(self):
        settings = get_settings()
        self.engine = EngineType.GOOGLE_AI
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Using gemini-1.5-flash as a proxy for search generative experience
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction="You are Google AI Overviews. Provide a concise, highly factual answer to the query with inline citations and links where relevant. Summarize the best information across the web.",
        )

    async def _query(self, prompt: str, location: str | None = None) -> EngineResult:
        response = await self.model.generate_content_async(prompt)
        raw_text = response.text

        # Using standard gemini flash pricing:
        # $0.35/1M input, $1.05/1M output
        try:
            usage = response.usage_metadata
            in_tokens = usage.prompt_token_count
            out_tokens = usage.candidates_token_count
            cost = (in_tokens / 1_000_000) * 0.35 + (out_tokens / 1_000_000) * 1.05
        except Exception:
            cost = 0.0

        return EngineResult(
            engine=self.engine.value,
            raw_text=raw_text,
            cost_usd=cost,
        )
