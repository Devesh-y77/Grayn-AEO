import asyncio
import json
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def run_test():
    # This is the exact URL of your deployed Railway MCP server
    url = "https://grayn-aeo-production.up.railway.app/mcp"
    print(f"Connecting to {url}...\n")
    
    try:
        # 1. Open the Server-Sent Events (SSE) connection
        headers = {"x-api-key": "mcp_live_4f8b2d1c6e9a73f50b4c8d1e2f3a9b7c5d6e4f1a2b8c9d0e3f7a1b4c5d6e9f0a"}
        async with sse_client(url, headers=headers) as streams:
            # 2. Establish the MCP Session
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                print("Successfully connected to Grayn MCP Server!\n")
                
                # 3. Ask the server what tools it has available
                print("Available Tools:")
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    print(f"  - {tool.name}")
                    
                print("\nTriggering a live AEO Analysis for 'perplexity.ai'...")
                print("   (Asking for 1 query across 1 model just for a quick test. Please wait ~5 seconds...)\n")
                
                # 4. Ask the server to run the specific tool
                result = await session.call_tool(
                    "trigger_aeo_analysis",
                    arguments={
                        "url": "perplexity.ai",
                        "location": "New York",
                        "queries": 1,
                        "models": ["openai"]
                    }
                )
                
                print("Analysis Complete! Here is the raw JSON returned to the bot:\n")
                
                # Parse and pretty-print the JSON result
                raw_text = result.content[0].text
                try:
                    parsed_json = json.loads(raw_text)
                    print(json.dumps(parsed_json, indent=2))
                except Exception:
                    print(raw_text)
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    # Required for Windows compatibility with asyncio
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(run_test())
