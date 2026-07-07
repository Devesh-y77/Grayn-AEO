"""
Grayn AEO — Anthropic Judge Service

The "judge" reads a raw AI engine answer and extracts structured data:
  • Brand/competitor mentions with position and sentiment
  • Cited URLs/domains with source type classification

Uses Anthropic Claude Haiku for fast, cheap, structured extraction.
"""

import json
import logging
import asyncio
import google.generativeai as genai
from app.config import get_settings
from app.models.schemas import (
    JudgeExtraction,
    MentionData,
    AttributeData,
    CitationData,
    Sentiment,
)

logger = logging.getLogger(__name__)

# ── System prompt for the judge ───────────────────────────

JUDGE_SYSTEM_PROMPT = """You are a precise data extraction agent. Given an AI assistant's answer, extract a MAXIMUM of the top 5 most prominent competitors/brands.
CRITICAL: Do NOT extract irrelevant products, generic nouns, or unassociated businesses (e.g., do not extract yogurt brands, strollers, or hospitals if the query is about fitness).

1. **Mentions**: Extract up to 5 brands/companies mentioned.
   - brand_name: exact name as written
   - is_target_brand: true if it matches the target brand (given below)
   - position: order of first appearance (1 = mentioned first)
   - sentiment: "positive", "neutral", or "negative" based on how the answer describes them
   - attributes: a list of qualities associated with the brand (e.g., pricing, speed).
     - name: name of the attribute (e.g., "Pricing")
     - sentiment: "positive", "neutral", or "negative"
     - competitor: (optional) if compared against a competitor, list the competitor name

2. **Citations**: Every URL or domain referenced as a source.
   - url: the full URL if available, otherwise the domain
   - domain: the root domain (e.g., "g2.com")
   - source_type: one of "review_site", "blog", "news", "official", "social", "other"

Return ONLY valid JSON matching this exact schema:
{
  "mentions": [{"brand_name": "", "is_target_brand": false, "position": 1, "sentiment": "neutral", "attributes": [{"name": "Pricing", "sentiment": "positive"}]}],
  "citations": [{"url": "", "domain": "", "source_type": "other"}]
}

Do not include any text outside the JSON object."""


# ── Mock judge (when no Anthropic key) ────────────────────

def _mock_judge_extraction(
    answer_text: str, target_brand: str
) -> JudgeExtraction:
    """Deterministic mock extraction for dev/test."""
    return JudgeExtraction(
        mentions=[
            MentionData(
                brand_name="Acme Corp",
                is_target_brand=("acme" in target_brand.lower()),
                position=1,
                sentiment=Sentiment.POSITIVE,
                attributes=[AttributeData(name="Reliability", sentiment=Sentiment.POSITIVE)],
            ),
            MentionData(
                brand_name="BrandTarget",
                is_target_brand=("brandtarget" in target_brand.lower()),
                position=2,
                sentiment=Sentiment.POSITIVE,
                attributes=[AttributeData(name="Pricing", sentiment=Sentiment.NEUTRAL, competitor="Acme Corp")],
            ),
            MentionData(
                brand_name="VisibilityPro",
                is_target_brand=("visibilitypro" in target_brand.lower()),
                position=3,
                sentiment=Sentiment.NEUTRAL,
                attributes=[],
            ),
            MentionData(
                brand_name="ContentRadar",
                is_target_brand=("contentradar" in target_brand.lower()),
                position=4,
                sentiment=Sentiment.NEUTRAL,
                attributes=[],
            ),
        ],
        citations=[
            CitationData(
                url="https://www.g2.com/products/acme",
                domain="g2.com",
                source_type="review_site",
            ),
            CitationData(
                url="https://www.capterra.com/p/brandtarget",
                domain="capterra.com",
                source_type="review_site",
            ),
            CitationData(
                url="https://blog.visibilitypro.com/features",
                domain="visibilitypro.com",
                source_type="blog",
            ),
        ],
    )


# ── Public API ────────────────────────────────────────────


async def extract_mentions_and_citations(
    answer_text: str,
    target_brand: str,
    brand_aliases: list[str] | None = None,
) -> JudgeExtraction:
    """
    Run the judge on an engine answer.
    Dynamically falls back across all available AI providers.
    """
    settings = get_settings()

    available_keys = []
    if settings.openai_available: available_keys.append("openai")
    if settings.groq_available: available_keys.append("groq")
    if settings.gemini_available: available_keys.append("gemini")
    if settings.anthropic_available: available_keys.append("anthropic")
    if settings.deepseek_available: available_keys.append("deepseek")

    if not available_keys:
        if settings.USE_MOCK_PROVIDERS:
            logger.info("Judge running in MOCK mode (No AI keys available). Returning empty to prevent DB pollution.")
            return JudgeExtraction(mentions=[], citations=[])
        else:
            raise ValueError("No API keys configured and USE_MOCK_PROVIDERS is False.")

    alias_hint = ""
    if brand_aliases:
        alias_hint = f" (also known as: {', '.join(brand_aliases)})"

    user_prompt = (
        f"INSTRUCTIONS: {JUDGE_SYSTEM_PROMPT}\n\n"
        f"Target brand: {target_brand}{alias_hint}\n\n"
        f"AI answer to analyse:\n---\n{answer_text}\n---"
    )

    import re
    last_exc = None

    for provider in available_keys:
        try:
            raw_json = ""
            if provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": user_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                raw_json = response.choices[0].message.content or ""

            elif provider == "groq":
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                response = await client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": user_prompt}],
                    response_format={"type": {"type": "json_object"}},
                    temperature=0.1,
                )
                raw_json = response.choices[0].message.content or ""

            elif provider == "deepseek":
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
                response = await client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": user_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                raw_json = response.choices[0].message.content or ""

            elif provider == "gemini":
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    generation_config={"response_mime_type": "application/json"}
                )
                response = await asyncio.to_thread(
                    model.generate_content,
                    user_prompt
                )
                raw_json = response.text or ""

            elif provider == "anthropic":
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                response = await client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=0.1,
                )
                raw_json = response.content[0].text or ""

            # Extract JSON from potential markdown wrapping
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_json, re.DOTALL)
            if match:
                raw_json = match.group(1)

            parsed = json.loads(raw_json)
            return JudgeExtraction(**parsed)

        except Exception as exc:
            logger.warning(f"Judge extraction failed with {provider}: {exc}")
            last_exc = exc
            continue

    if settings.USE_MOCK_PROVIDERS:
        logger.warning("All AI providers failed for judge extraction, but returning empty extraction instead of mock data to prevent database pollution.", exc_info=last_exc)
        return JudgeExtraction(mentions=[], citations=[])

    raise RuntimeError(f"Judge extraction failed across all available providers. Last error: {last_exc}")
