import asyncio
import json
import httpx
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def run_test():
    url = "http://localhost:8000/mcp"
    print(f"Connecting to {url}...\n")
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv("backend/.env")
        api_key = os.environ.get("MCP_API_KEY", "")
        headers = {"x-api-key": api_key} if api_key else {}
        
        async with sse_client(url, headers=headers, timeout=300.0, sse_read_timeout=300.0) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                print("Successfully connected to Grayn MCP Server!\n")
                result = await session.call_tool(
                    "trigger_aeo_analysis",
                    arguments={
                        "url": "netflix.com",
                        "location": "India",
                        "queries": 2,
                        "models": ["openai", "perplexity"],
                        "passes": 3
                    }
                )
                print(result.content[0].text)
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_test())
