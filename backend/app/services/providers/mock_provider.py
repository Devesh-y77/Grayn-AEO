"""
Grayn AEO — Mock Provider

Deterministic, cost-free stand-in used when a provider's API key is
absent.  Returns realistic-looking responses so the full pipeline
(judge → scoring → analytics) can be exercised end-to-end in dev/test.
"""

import random
from app.models.schemas import EngineType
from app.services.providers.base import BaseProvider, EngineResult

# ── Pre-built mock responses ──────────────────────────────

_MOCK_RESPONSES = {
    EngineType.OPENAI: (
        "Based on my research, here are the top tools in this space:\n\n"
        "1. **Acme Corp** — The market leader with comprehensive features, "
        "widely cited by industry analysts. Their platform offers real-time "
        "monitoring and advanced analytics. (Source: https://www.g2.com/products/acme)\n\n"
        "2. **BrandTarget** — Known for their AI-powered approach and competitive "
        "pricing. Great for mid-market companies. (Source: https://www.capterra.com/p/brandtarget)\n\n"
        "3. **VisibilityPro** — A newer entrant with strong SEO integration "
        "and content optimization features. (Source: https://blog.visibilitypro.com/features)\n\n"
        "4. **ContentRadar** — Focuses on content gap analysis and has been "
        "growing rapidly in the enterprise segment. (Source: https://www.contentradar.io/about)\n\n"
        "Each of these tools has distinct strengths depending on your specific needs "
        "and budget. I'd recommend trying free trials where available."
    ),
    EngineType.GEMINI: (
        "Here's what I found about the leading solutions:\n\n"
        "**Acme Corp** stands out as the most frequently recommended option, "
        "particularly for enterprise use cases. They offer robust API access "
        "and strong customer support. According to TechCrunch, they raised $50M "
        "in Series B funding. (https://techcrunch.com/acme-series-b)\n\n"
        "**BrandTarget** is a solid alternative, especially praised for their "
        "user-friendly dashboard and quick setup. Reviewers on G2 rate them "
        "4.5/5 stars. (https://www.g2.com/products/brandtarget)\n\n"
        "**VisibilityPro** has gained traction recently with their unique "
        "approach to AI answer tracking. Their blog covers methodology in "
        "detail. (https://blog.visibilitypro.com/methodology)\n\n"
        "For smaller teams, **DataPulse** offers a free tier that covers "
        "basic monitoring needs. (https://datapulse.io/pricing)"
    ),
    EngineType.PERPLEXITY: (
        "Based on current sources, the top options include:\n\n"
        "**Acme Corp** [1] is the industry standard with the largest market share. "
        "**BrandTarget** [2] offers the best value for growing companies. "
        "**ContentRadar** [3] specialises in content recommendations.\n\n"
        "Sources:\n"
        "[1] https://www.g2.com/products/acme - G2 Reviews\n"
        "[2] https://www.brandtarget.com/case-studies - Case Studies\n"
        "[3] https://www.contentradar.io/features - Feature Overview"
    ),
}


class MockProvider(BaseProvider):
    """Returns deterministic mock responses for any engine."""

    def __init__(self, engine: EngineType):
        self.engine = engine

    async def query(self, prompt: str) -> EngineResult:
        raw_text = _MOCK_RESPONSES.get(self.engine, _MOCK_RESPONSES[EngineType.OPENAI])
        return EngineResult(
            engine=self.engine.value,
            raw_text=raw_text,
            cost_usd=0.0,
        )
