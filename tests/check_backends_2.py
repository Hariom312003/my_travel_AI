import requests

urls = [
    "https://mytravelai-api.onrender.com",
    "https://my-travel-ai-api.onrender.com",
    "https://mytravelai-backend.onrender.com",
    "https://my-travel-ai-backend.onrender.com",
    "https://mytravelai-api.railway.app",
    "https://my-travel-ai-api.railway.app",
]

for url in urls:
    try:
        r = requests.get(url + "/health", timeout=3)
        print(f"URL: {url} -> Status: {r.status_code}, Response: {r.text}")
    except Exception as e:
        print(f"URL: {url} -> Failed: {e}")
