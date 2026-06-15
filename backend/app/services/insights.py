import logging
from app.models.schemas import FullReport
from app.config import get_settings
from app.services.providers.base import get_provider
from app.models.schemas import EngineType

logger = logging.getLogger(__name__)

INSIGHT_SYSTEM_PROMPT = """You are an expert Answer Engine Optimization (AEO) and marketing analyst.
Given the following data about a brand's visibility in AI search engines (ChatGPT, Claude, Perplexity, etc.), write a highly strategic, 3-sentence "Latest AI Insight" summary for the user.

Your goal:
1. Sentence 1: State the target brand's overall visibility and top-level performance.
2. Sentence 2: Identify a specific threat (e.g., a competitor capturing share, or a platform where visibility dropped).
3. Sentence 3: Give one clear, actionable recommendation to close the gap or improve (e.g., referencing positive attributes or creating comparison content).

Do NOT use placeholders. Do NOT write more than 3 sentences. Write it in second-person ("You"). Make it sound like a premium SaaS dashboard insight.
"""

async def generate_report_insight(report_data: dict) -> str:
    """Generate a strategic insight paragraph from the report data."""
    settings = get_settings()

    available_providers = []
    if settings.anthropic_available:
        available_providers.append(EngineType.CLAUDE)
    if settings.openai_available:
        available_providers.append(EngineType.OPENAI)
    if settings.gemini_available:
        available_providers.append(EngineType.GEMINI)
    if settings.groq_available:
        available_providers.append(EngineType.GROQ)
    if settings.deepseek_available:
        available_providers.append(EngineType.DEEPSEEK)

    if not available_providers:
        if settings.USE_MOCK_PROVIDERS:
            # Fallback mock insight
            ws = report_data.get("workspace", {})
            bname = ws.get("brand_name", "Your brand")
            vis = report_data.get("visibility", {}).get("visibility_pct", 0)
            return f"{bname} currently maintains {vis}% visibility across AI engines. Competitors are gaining ground in certain platforms. Focus on publishing clear technical comparisons to regain momentum."
        else:
            logger.warning("No API keys available to generate AI insight.")
            return "No AI providers configured to generate insights."

    user_prompt = f"{INSIGHT_SYSTEM_PROMPT}\n\nReport Data JSON:\n{report_data}"

    last_error = None
    for provider_type in available_providers:
        try:
            provider = get_provider(provider_type)
            if hasattr(provider, "__aenter__"):
                async with provider as p:
                    res = await p.query(user_prompt)
            else:
                res = await provider.query(user_prompt)
            
            # If the provider swallowed an exception and returned mock text, but we don't want mock text
            if not settings.USE_MOCK_PROVIDERS and "A review of the landscape" in res.raw_text:
                raise Exception("Provider returned mock fallback string instead of real API response.")
                
            return res.raw_text.strip()
        except Exception as e:
            logger.error(f"Failed to generate AI insight with {provider_type.value}: {e}")
            last_error = e

    return "Failed to generate AI insight. All configured AI providers returned errors."
