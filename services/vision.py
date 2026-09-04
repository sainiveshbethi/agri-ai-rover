import os
import io
import json
import re
from typing import Dict, Any, Optional
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Ensure .env file in project root is loaded
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    load_dotenv(override=True)

class SeedClassifierAdapter:
    """Pluggable adapter interface for future dedicated local seed classification models."""
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.is_enabled = False

    def predict(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        if not self.is_enabled:
            return None
        return {
            "seed_type": "Unknown",
            "confidence": 0.0,
            "is_unsupported": True
        }

class VisionAIService:
    def __init__(self, seed_adapter: Optional[SeedClassifierAdapter] = None):
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
        raw_key = os.environ.get("GEMINI_API_KEY", "")
        self.api_key = raw_key.strip("'\" \n\r\t")
        self.seed_adapter = seed_adapter or SeedClassifierAdapter()
        # Supported Flash vision models for google.genai SDK
        self.models = ["gemini-3.6-flash", "gemini-3.5-flash"]

    def is_configured(self) -> bool:
        """Checks if GEMINI_API_KEY is configured and valid."""
        return bool(self.api_key and len(self.api_key) > 5 and not self.api_key.startswith("PASTE_"))

    @staticmethod
    def compress_and_resize_image(pil_image: Image.Image, max_dim: int = 1024, quality: int = 80) -> Image.Image:
        """Optimizes uploaded image by resizing to max 1024px and compressing to JPEG quality 80%.
        Drastically reduces network payload size for fast analysis and minimal memory footprint.
        """
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')

        w, h = pil_image.size
        if max(w, h) > max_dim:
            pil_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        pil_image.save(buf, format='JPEG', quality=quality, optimize=True)
        buf.seek(0)
        
        return Image.open(buf)

    def _get_genai_client() -> genai.Client:
        """Returns initialized google.genai Client with sanitized API key."""
        if not self.is_configured():
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in environment variables.")
        return genai.Client(api_key=self.api_key)

    def _call_gemini_api(self, pil_image: Image.Image, prompt: str) -> str:
        """Executes a single fast vision model request using official google-genai SDK."""
        if not self.is_configured():
            raise ValueError("Gemini API key missing. Please set GEMINI_API_KEY in Render environment variables.")

        client = genai.Client(api_key=self.api_key)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )

        last_exception = None
        for model_name in self.models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[pil_image, prompt],
                    config=config
                )
                if response and response.text:
                    return response.text
            except Exception as ex:
                last_exception = ex
                continue

        err_msg = str(last_exception) if last_exception else "No response returned from Gemini API"
        if self.api_key and self.api_key in err_msg:
            err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")

        raise RuntimeError(f"Gemini Vision API execution failed: {err_msg}")

    def test_connection(self) -> Dict[str, Any]:
        """Tests live API connectivity with Gemini API using google-genai SDK."""
        if not self.is_configured():
            return {
                "status": "not_configured",
                "configured": False,
                "engine": "Gemini Vision AI",
                "model": "None",
                "message": "Gemini API key is not configured in environment variables."
            }

        try:
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            
            # Lightweight text ping without image payload
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents='Return ONLY valid JSON: {"status": "ok", "message": "connected"}',
                config=config
            )

            if response and response.text:
                return {
                    "status": "connected",
                    "configured": True,
                    "engine": "Gemini Vision AI",
                    "model": "gemini-3.6-flash",
                    "message": "Gemini Vision API is connected and responding normally!"
                }
            else:
                raise RuntimeError("Empty response received from Gemini API test.")

        except Exception as e:
            err_msg = str(e)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")
            return {
                "status": "error",
                "configured": True,
                "engine": "Gemini Vision AI",
                "model": "Unknown",
                "message": f"Gemini API test failed: {err_msg}"
            }

    def analyze_crop_image(self, pil_image: Image.Image) -> Dict[str, Any]:
        """Compresses image and sends concise Gemini Vision request using google-genai SDK."""
        
        # Step 1: Pre-process & compress image for rapid network transfer
        optimized_image = self.compress_and_resize_image(pil_image, max_dim=1024, quality=80)

        # Step 2: Concise, high-speed prompt requesting ONLY visual observations
        prompt = """
Analyze the image quickly as an expert agricultural pathologist. Return ONLY valid JSON:
{
  "identified_item": "Crop/Seed/Plant name in English (e.g. 'Tomato', 'Paddy / Rice', 'Wheat', 'Maize', 'Soybean', 'Cotton', 'Groundnut', 'Chickpea', 'Green Gram', 'Black Gram', 'Mustard', 'Sunflower', 'Potato', 'Chilli', 'Brinjal'). If non-agricultural or unclear, return 'Not a crop/seed or unable to identify' or 'Unknown'.",
  "scientific_name": "Botanical species name if identifiable, or empty string",
  "category": "One of: 'seed/grain', 'crop', 'vegetable', 'fruit', 'leaf', 'plant', 'unknown/non-agricultural object'",
  "confidence": Float decimal 0.0 to 1.0 (Return < 0.40 if uncertain),
  "candidates": [{"name": "Item name", "confidence": 0.9}],
  "visible_condition": "One of: 'Healthy', 'Fair', 'Poor', 'Damaged', 'Unknown'",
  "visible_damage_or_symptoms": "Short description of visible rot, spots, mold, discoloration, insect damage, or 'None detected'",
  "explanation": "Max 1-2 concise sentences describing visual features."
}

RULES:
- Rotten or spoiled items must keep their species identity if recognizable, but visible_condition MUST be 'Poor' or 'Damaged'.
- For cars, shoes, humans, or non-agricultural objects, set identified_item: "Not a crop/seed or unable to identify", category: "unknown/non-agricultural object", confidence: 0.0.
"""

        try:
            raw_text = self._call_gemini_api(optimized_image, prompt)
            
            clean_text = raw_text.strip()
            if clean_text.startswith("```"):
                clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
                clean_text = re.sub(r"\s*```$", "", clean_text)

            parsed = json.loads(clean_text)
            
            identified_item = str(parsed.get("identified_item", "Unknown")).strip()
            category = str(parsed.get("category", "unknown/non-agricultural object")).strip()
            confidence = float(parsed.get("confidence", 0.0))
            visible_condition = str(parsed.get("visible_condition", "Unknown")).strip()
            visible_damage_or_symptoms = str(parsed.get("visible_damage_or_symptoms", "None detected")).strip()
            explanation = str(parsed.get("explanation", "")).strip()
            candidates = parsed.get("candidates", [])

            if confidence < 0.45 and identified_item not in ["Not a crop/seed or unable to identify", "Unknown"]:
                identified_item = "Unknown"
                explanation = f"Low confidence identification ({int(confidence*100)}%). Unable to classify reliably."

            return {
                "identified_item": identified_item,
                "crop_name": identified_item,
                "scientific_name": str(parsed.get("scientific_name", "")).strip(),
                "category": category,
                "confidence": confidence,
                "candidates": candidates,
                "visible_condition": visible_condition,
                "visible_condition_status": visible_condition,
                "visible_damage_or_symptoms": visible_damage_or_symptoms,
                "visible_abnormalities": visible_damage_or_symptoms,
                "explanation": explanation,
                "recommendations": "",
                "is_suitable": confidence >= 0.40 and category != "unknown/non-agricultural object"
            }

        except json.JSONDecodeError as je:
            print(f"[VisionAIService] JSON Parse Error: {je}")
            return {
                "identified_item": "Unknown",
                "crop_name": "Unknown",
                "scientific_name": "",
                "category": "unknown/non-agricultural object",
                "confidence": 0.0,
                "candidates": [],
                "visible_condition": "Unknown",
                "visible_condition_status": "Unknown",
                "visible_damage_or_symptoms": "AI response parsing error",
                "visible_abnormalities": "AI response parsing error",
                "explanation": "Image formatting error. Please upload a clearer photograph.",
                "recommendations": "",
                "is_suitable": False
            }
        except Exception as e:
            raise e
