import os
from dotenv import load_dotenv
from google import genai
from PIL import Image

# 1. Load .env file with override
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path, override=True)

api_key = os.environ.get("GEMINI_API_KEY", "").strip("'\" \n\r\t")

print("==================================================")
print("1. ENV LOAD VERIFICATION:")
print(f"   .env Path: {env_path}")
print(f"   Key Loaded Length: {len(api_key)}")
print(f"   Key Prefix: {api_key[:6]}...")
print(f"   Key Suffix: ...{api_key[-6:]}")
print("==================================================")

# 2. Test Simple Backend Gemini Request
client = genai.Client(api_key=api_key)

models_to_try = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash"
]

print("2. TESTING NATIVE GEMINI AUTHENTICATION:")
working_model = None

for m_name in models_to_try:
    try:
        res = client.models.generate_content(
            model=m_name,
            contents="Say 'GEMINI_AUTH_SUCCESS' if authentication works."
        )
        if res and res.text:
            print(f"   [SUCCESS] Model '{m_name}' authenticated cleanly!")
            print(f"   Response Output: {res.text.strip()}")
            working_model = m_name
            break
    except Exception as e:
        print(f"   [FAILED] Model '{m_name}': {str(e)[:120]}")

print("==================================================")

# 3. Test Image Analysis Pipeline with Working Model
if working_model:
    print(f"3. TESTING MULTIMODAL IMAGE ANALYSIS WITH '{working_model}':")
    img = Image.new('RGB', (100, 100), color='green')
    try:
        img_res = client.models.generate_content(
            model=working_model,
            contents=[img, "Describe what color and object is in this image in one short sentence."]
        )
        print(f"   [SUCCESS] Image Vision Result: {img_res.text.strip()}")
    except Exception as e:
        print(f"   [FAILED] Image Vision Failed: {e}")
print("==================================================")
