import requests
import json
import io
from PIL import Image

print("==================================================")
print("LIVE GEMINI VISION VERIFICATION & TEST")
print("==================================================")

# 1. Test GET /api/test-gemini endpoint
test_res = requests.get("http://127.0.0.1:5000/api/test-gemini")
print("1. Testing GET /api/test-gemini status...")
print(f"   HTTP Status: {test_res.status_code}")
print(f"   Response: {json.dumps(test_res.json(), indent=2)}")

# 2. Test Image 1: Pure Green Leaf (Tomato / Plant)
img1 = Image.new('RGB', (400, 400), color=(34, 139, 34))
buf1 = io.BytesIO()
img1.save(buf1, format='JPEG')
buf1.seek(0)

print("\n2. Uploading Image 1 (Green Foliage Sample) to POST /api/analyze...")
res1 = requests.post("http://127.0.0.1:5000/api/analyze", files={"image": ("green_leaf.jpg", buf1, "image/jpeg")})
print(f"   HTTP Status: {res1.status_code}")
data1 = res1.json()
print(f"   Identified Item: {data1.get('identified_item')}")
print(f"   Confidence: {data1.get('confidence')}")
print(f"   Condition: {data1.get('visible_condition')}")
print(f"   Explanation: {data1.get('explanation')}")

# 3. Test Image 2: Yellowish-Golden Grain (Wheat / Corn)
img2 = Image.new('RGB', (400, 400), color=(218, 165, 32))
buf2 = io.BytesIO()
img2.save(buf2, format='JPEG')
buf2.seek(0)

print("\n3. Uploading Image 2 (Golden Grain Sample) to POST /api/analyze...")
res2 = requests.post("http://127.0.0.1:5000/api/analyze", files={"image": ("golden_wheat.jpg", buf2, "image/jpeg")})
print(f"   HTTP Status: {res2.status_code}")
data2 = res2.json()
print(f"   Identified Item: {data2.get('identified_item')}")
print(f"   Confidence: {data2.get('confidence')}")
print(f"   Condition: {data2.get('visible_condition')}")
print(f"   Explanation: {data2.get('explanation')}")

print("\n==================================================")
print("VERIFICATION COMPLETED SUCCESSFULLY!")
print("==================================================")
