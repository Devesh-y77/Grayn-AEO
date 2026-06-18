import asyncio
import os
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

async def test_models():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    print(f"API Key present: {bool(api_key)}")
    
    if not api_key:
        print("No API key found in .env")
        return
        
    client = AsyncAnthropic(api_key=api_key)
    
    models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
        "claude-2.1"
    ]
    
    for m in models:
        try:
            print(f"Testing {m}...")
            response = await client.messages.create(
                model=m,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            print(f"SUCCESS for {m}: {response.content[0].text}")
        except Exception as e:
            print(f"FAILED for {m}: {e}")

if __name__ == "__main__":
    asyncio.run(test_models())
