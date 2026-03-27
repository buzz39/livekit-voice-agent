"""Query deployed API for prompt content."""
import os, httpx
from dotenv import load_dotenv
load_dotenv()

base = os.getenv("API_BASE_URL", "https://livekit-outbound-api.tinysaas.fun")
key = os.getenv("API_SECRET_KEY", "")
headers = {"x-api-key": key} if key else {}

# Get prompt content for IDs 1 and 2
for pid in [1, 2]:
    r = httpx.get(f"{base}/dashboard/prompt/{pid}", headers=headers, timeout=15)
    if r.status_code == 200:
        data = r.json()
        name = data.get("name", "?")
        content = data.get("content", "")
        print(f"=== PROMPT {pid}: {name} ===")
        print(content[:2000])
        if len(content) > 2000:
            print("...[truncated]")
        print()

# Also get the AI config details
r = httpx.get(f"{base}/dashboard/ai-config", headers=headers, timeout=15)
print("=== ACTIVE AI CONFIG ===")
print(r.status_code, r.text[:1000])
