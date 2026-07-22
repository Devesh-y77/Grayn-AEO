"""
Grayn AEO — Discovery Service

Automated onboarding flow:
1. Fetch homepage of client's URL.
2. Extract meta info and body text.
3. Pass to OpenAI (or active LLM) to extract brand_name, suggested_competitors, queries, and themes.
"""

import httpx
from bs4 import BeautifulSoup
import json
import logging
from app.services.providers.base import get_provider, EngineType

logger = logging.getLogger(__name__)

DISCOVERY_SYSTEM_PROMPT = """You are an expert SEO and Answer Engine Optimization analyst.
You will be provided with the text content of a company's website homepage.
Based on this content, extract the following:
1. `brand_name`: The canonical name of the brand.
2. `suggested_competitors`: A list of exactly 10 major competitors in this industry. For each, provide `brand_name`, `domain`, and `aliases`.
3. `suggested_queries`: A list of {num_queries} high-value SEO and AEO search queries that prospective customers use during the research and evaluation phase BEFORE they know about this specific brand.
- Focus strictly on NON-BRANDED, high-intent commercial and informational queries.
- Examples: "Best [category] software", "Top [category] apps for [use case]", "How to [solve problem] without [pain point]".
- STRICTLY EXCLUDE any queries that contain the brand's own name (e.g., "[Brand] app reviews", "How to use [Brand]", "[Brand] features"). We only want to track share of voice for generic industry terms and competitor alternatives.
4. `themes`: A list of 3 overarching topic clusters (e.g. "Serverless Hosting", "Edge Computing").

CRITICAL INSTRUCTION: If the Website Content is empty or very short, you MUST infer the brand name, competitors, queries, and themes purely from the URL domain provided using your training knowledge. NEVER apologize, ask for more content, or refuse the prompt. ALWAYS return valid JSON.

Return ONLY valid JSON matching this exact schema:
{
  "brand_name": "Company Name",
  "suggested_competitors": [
    {"brand_name": "Competitor", "domain": "competitor.com", "aliases": ["Comp", "Competitor Inc"]}
  ],
  "suggested_queries": [
    {"text": "Query 1", "attributes": ["branded"]},
    {"text": "Query 2", "attributes": ["non-branded", "comparison"]}
  ],
  "themes": ["Theme 1", "Theme 2"]
}
Do not include markdown blocks, just the JSON.
"""

async def run_discovery(url: str, num_queries: int = 10) -> dict:
    if not url.startswith("http"):
        url = "https://" + url

    html = ""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        # Ignore fetch failures and just pass the raw URL to the LLM
        print(f"Discovery scrape failed: {e}")
        pass

    soup = BeautifulSoup(html, "html.parser")
    
    # Extract title and description
    title = soup.title.string if soup.title else ""
    meta_desc = ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag:
        meta_desc = desc_tag.get("content", "")

    # Extract some text to give to LLM (limit to ~3000 chars)
    text_content = soup.get_text(separator=" ", strip=True)
    snippet = f"URL: {url}\nTitle: {title}\nDescription: {meta_desc}\n\nContent:\n{text_content[:3000]}"

    # We use OpenAI by default for discovery extraction (or fallback to Gemini/Mock if not available)
    try:
        provider = get_provider(EngineType.OPENAI)
    except ValueError:
        try:
            provider = get_provider(EngineType.GEMINI)
        except ValueError:
            provider = get_provider(EngineType.GROQ)

    prompt = f"{DISCOVERY_SYSTEM_PROMPT.replace('{num_queries}', str(num_queries))}\n\nWebsite Content:\n{snippet}"
    result = await provider.query(prompt)

    try:
        raw = result.raw_text.strip()
        if raw.startswith("```json"):
            raw = raw[7:-3]
        elif raw.startswith("```"):
            raw = raw[3:-3]
        
        parsed = json.loads(raw.strip())
        return parsed
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse LLM discovery response. Raw: {result.raw_text}")
        domain = url.split("://")[-1].split("/")[0].replace("www.", "")
        return {
            "brand_name": domain.split(".")[0].title(),
            "suggested_queries": [
                {"text": f"{domain} alternatives"},
                {"text": f"what is {domain}"},
                {"text": f"best tools like {domain}"}
            ][:num_queries]
        }
