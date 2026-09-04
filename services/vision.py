import os
import io
import json
import re
from typing import Dict, Any, Optional
from PIL import Image
from dotenv import load_dotenv

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

    def is_configured(self) -> bool:
        """Checks if GEMINI_API_KEY is configured and valid."""
        return bool(self.api_key and self.api_key != "PASTE_MY_GEMINI_API_KEY_HERE" and len(self.api_key) > 5)

    @staticmethod
    def compress_and_resize_image(pil_image: Image.Image, max_dim: int = 1024, quality: int = 80) -> Image.Image:
        """Optimizes uploaded image by resizing to max 1024px and compressing to JPEG quality 80%.
        Drastically reduces network payload size (from ~5MB to ~80KB) for 5x faster Gemini analysis.
        """
        # Convert mode to RGB if RGBA/Palette
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')

        # Downscale if width or height > max_dim
        w, h = pil_image.size
        if max(w, h) > max_dim:
            pil_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Compress to JPEG buffer
        buf = io.BytesIO()
        pil_image.save(buf, format='JPEG', quality=quality, optimize=True)
        buf.seek(0)
        
        return Image.open(buf)

    def _call_gemini_api(self, pil_image: Image.Image, prompt: str) -> str:
        """Executes a single fast vision model request using official google-genai SDK."""
        if not self.is_configured():
            raise ValueError("AI API key is not configured. Please set GEMINI_API_KEY in .env file.")

        # Fast multimodal models prioritizing speed
        fast_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.5-flash"
        ]

        last_exception = None

        # Try official google-genai SDK
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key)
            
            # Configure structured JSON output + temperature for maximum speed
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            
            for model_name in fast_models:
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
        except ImportError:
            pass

        # Fallback to google-generativeai SDK if needed
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            for model_name in fast_models:
                try:
                    model = genai.GenerativeModel(
                        model_name,
                        generation_config={"response_mime_type": "application/json", "temperature": 0.1}
                    )
                    response = model.generate_content([pil_image, prompt])
                    if response and response.text:
                        return response.text
                except Exception as ex:
                    last_exception = ex
                    continue
        except Exception as e:
            last_exception = e

        err_msg = str(last_exception)
        if self.api_key and self.api_key in err_msg:
            err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")

        raise RuntimeError(f"Gemini Vision API execution failed: {err_msg}")

    def test_connection(self) -> Dict[str, Any]:
        """Tests live API connectivity with Gemini Vision models."""
        if not self.is_configured():
            return {
                "status": "not_configured",
                "configured": False,
                "engine": "Gemini Vision AI",
                "model": "None",
                "message": "Gemini API key is not configured in .env file."
            }

        try:
            test_img = Image.new('RGB', (10, 10), color='green')
            prompt = 'Analyze this test sample. Return ONLY valid JSON: {"identified_item": "Test", "status": "ok"}'
            raw_text = self._call_gemini_api(test_img, prompt)
            return {
                "status": "connected",
                "configured": True,
                "engine": "Gemini Vision AI",
                "model": "gemini-3.5-flash-lite",
                "message": "Gemini Vision API is connected and responding normally!"
            }
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
        """Compresses image and sends ONE concise fast Gemini Vision request."""
        
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
