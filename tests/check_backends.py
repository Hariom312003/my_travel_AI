import requests

urls = [
    "https://mytravelai.onrender.com",
    "https://my-travel-ai.onrender.com",
    "https://mytravelai.fly.dev",
    "https://my-travel-ai.fly.dev",
    "https://mytravelai.railway.app",
    "https://my-travel-ai.railway.app",
    "http://mytravelai-8ldd9q3yfo3k2vlldjg6y3.streamlit.app:8000",
]

for url in urls:
    try:
        r = requests.get(url, timeout=3)
        print(f"URL: {url} -> Status: {r.status_code}, Response: {r.text}")
    except Exception as e:
        print(f"URL: {url} -> Failed: {e}")
