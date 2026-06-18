import asyncio
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_key = os.environ.get("GEMINI_API_KEY")
    print("API Key present:", bool(api_key))
    if not api_key: return
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        res = await asyncio.to_thread(model.generate_content, "Hello")
        print("Gemini 2.0 Success:", res.text)
    except Exception as e:
        print("Gemini 2.0 Error:", e)

    model2 = genai.GenerativeModel("gemini-1.5-flash")
    try:
        res = await asyncio.to_thread(model2.generate_content, "Hello")
        print("Gemini 1.5 Success:", res.text)
    except Exception as e:
        print("Gemini 1.5 Error:", e)

if __name__ == "__main__":
    asyncio.run(test())
