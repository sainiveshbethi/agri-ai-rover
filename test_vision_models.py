import os
from dotenv import load_dotenv
from google import genai
from PIL import Image

load_dotenv(override=True)
key = os.environ.get("GEMINI_API_KEY", "").strip("'\" \n\r\t")
client = genai.Client(api_key=key)

img = Image.new('RGB', (100, 100), color='green')

models_to_test = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite"
]

for m in models_to_test:
    try:
        res = client.models.generate_content(
            model=m,
            contents=[img, "Describe this sample briefly."]
        )
        print(f"[OK] {m}: {res.text.strip()}")
    except Exception as e:
        print(f"[ERR] {m}: {e}")
