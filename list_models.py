import os
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)
key = os.environ.get("GEMINI_API_KEY", "").strip("'\" \n\r\t")
print(f"Key loaded: {key[:6]}...{key[-4:]}")

client = genai.Client(api_key=key)

for m in client.models.list():
    if "generateContent" in getattr(m, 'supported_actions', []) or "generateContent" in getattr(m, 'supported_generation_methods', []):
        print(f"Model: {m.name}")
