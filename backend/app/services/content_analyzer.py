import httpx
import asyncio
from bs4 import BeautifulSoup
from app.services.providers.gemini_provider import GeminiProvider
import traceback

async def scrape_url(url: str) -> str:
    """Fetch and extract readable text from a URL."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Mask as a normal browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            }
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "aside"]):
                script.decompose()
                
            text = soup.get_text(separator=' ', strip=True)
            # Truncate to avoid blowing up context window (roughly 1500 words)
            return text[:10000]
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return ""


async def analyze_content_gaps(urls: list[str], prompt_text: str, brand_name: str) -> str:
    """
    Scrape the URLs and ask Gemini to generate an organic content strategy.
    """
    if not urls:
        return "No competitor URLs provided."

    # Scrape all URLs concurrently
    tasks = [scrape_url(u) for u in urls]
    results = await asyncio.gather(*tasks)
    
    # Combine text
    combined_text = ""
    for idx, (url, text) in enumerate(zip(urls, results)):
        if text:
            combined_text += f"\n\n--- Source {idx+1}: {url} ---\n{text}\n"

    if not combined_text.strip():
        return "Failed to extract content from the provided URLs (they may block scraping or be inaccessible)."

    system_prompt = (
        "You are an expert SEO Content Strategist. Your client is '{brand_name}'. "
        "The target keyword/topic is '{prompt_text}'. "
        "Below is the scraped text from top-ranking competitor articles that AI engines currently cite for this topic. "
        "Analyze the content carefully. What themes, headings, structures, and questions do these competitors cover? "
        "Generate a highly-detailed 'Content Brief' for our client to write a better, more comprehensive organic article. "
        "You MUST output valid JSON ONLY, strictly matching this schema:\n"
        "{{\n"
        '  "Goal": "A 1-2 sentence description of the content goal",\n'
        '  "Must_Answer_Questions": ["Question 1", "Question 2", "Question 3"],\n'
        '  "Competitor_To_Beat": "The name or URL of the top competitor to beat"\n'
        "}}\n"
        "No markdown code blocks, no intro, no outro. Just raw JSON."
    )

    import google.generativeai as genai
    from app.config import get_settings
    
    settings = get_settings()
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=system_prompt.format(brand_name=brand_name, prompt_text=prompt_text)
    )
    
    try:
        response = await asyncio.to_thread(
            model.generate_content,
            f"COMPETITOR CONTENT:\n{combined_text}"
        )
        return response.text or "Failed to generate strategy."
    except Exception as e:
        print(f"Gemini API failed: {str(e)}. Falling back to OpenAI.")
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt.format(brand_name=brand_name, prompt_text=prompt_text),
                    },
                    {"role": "user", "content": f"COMPETITOR CONTENT:\n{combined_text}"},
                ],
                temperature=0.7,
                max_tokens=3000,
            )
            return response.choices[0].message.content or "Failed to generate strategy via fallback."
        except Exception as fallback_e:
            traceback.print_exc()
            return f"Error analyzing content gaps: Gemini failed ({str(e)}), OpenAI fallback failed ({str(fallback_e)})"
