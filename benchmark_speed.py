import time
from PIL import Image
from services.vision import VisionAIService

print("==================================================")
print("FAST GEMINI VISION PIPELINE BENCHMARK")
print("==================================================")

v = VisionAIService()

# 1. Create a large test image (2000 x 2000 px) to test downscaling + compression
large_img = Image.new('RGB', (2000, 2000), color='green')

start_time = time.time()
print("1. Optimizing image (downscaling to 1024px + JPEG 80% compression)...")
compressed = v.compress_and_resize_image(large_img)
opt_time = time.time() - start_time
print(f"   Image optimized in {opt_time:.3f} seconds. Optimized size: {compressed.size}")

# 2. Benchmark full Gemini Vision analysis request
print("2. Sending single fast Gemini Vision request...")
api_start = time.time()
result = v.analyze_crop_image(large_img)
total_time = time.time() - start_time

print(f"   Total Pipeline Time: {total_time:.2f} seconds!")
print("==================================================")
print("Result JSON:")
import json
print(json.dumps(result, indent=2))
print("==================================================")
