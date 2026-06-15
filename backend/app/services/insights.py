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

    # Try to find an available provider
    provider_type = None
    if settings.anthropic_available:
        provider_type = EngineType.ANTHROPIC
    elif settings.openai_available:
        provider_type = EngineType.OPENAI
    elif settings.gemini_available:
        provider_type = EngineType.GEMINI
    elif settings.groq_available:
        provider_type = EngineType.GROQ
    elif settings.deepseek_available:
        provider_type = EngineType.DEEPSEEK

    if not provider_type:
        if settings.USE_MOCK_PROVIDERS:
            # Fallback mock insight
            ws = report_data.get("workspace", {})
            bname = ws.get("brand_name", "Your brand")
            vis = report_data.get("visibility", {}).get("visibility_pct", 0)
            return f"{bname} currently maintains {vis}% visibility across AI engines. Competitors are gaining ground in certain platforms. Focus on publishing clear technical comparisons to regain momentum."
        else:
            logger.warning("No API keys available to generate AI insight.")
            return "No AI providers configured to generate insights."

    try:
        provider = get_provider(provider_type)
        user_prompt = f"{INSIGHT_SYSTEM_PROMPT}\n\nReport Data JSON:\n{report_data}"
        
        # Some providers need an async context manager
        if hasattr(provider, "__aenter__"):
            async with provider as p:
                res = await p.query(user_prompt)
        else:
            res = await provider.query(user_prompt)
            
        return res.raw_text.strip()
    except Exception as e:
        logger.error(f"Failed to generate AI insight: {e}")
        return "Failed to generate AI insight due to an API error."
