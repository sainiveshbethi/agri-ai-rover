from dotenv import load_dotenv
load_dotenv()

from services.vision import VisionAIService
from PIL import Image

v = VisionAIService()
print("API Key configured:", v.is_configured())

img = Image.new('RGB', (200, 200), color='red')
result = v.analyze_crop_image(img)
print("Analysis Output:")
import json
print(json.dumps(result, indent=2))
