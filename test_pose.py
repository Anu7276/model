import requests
import json

url = "http://127.0.0.1:5000/process_pose"
# 17 landmarks
landmarks = [{"x": 0.5, "y": 0.5, "visibility": 0.8} for _ in range(17)]
payload = {
    "exercise_type": "pushup",
    "landmarks": landmarks
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
