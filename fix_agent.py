"""Link roofing_agent to Aisha prompt (id=1)."""
import os, httpx
from dotenv import load_dotenv
load_dotenv()

base = os.getenv("API_BASE_URL", "https://livekit-outbound-api.tinysaas.fun")
key = os.getenv("API_SECRET_KEY", "")
h = {"x-api-key": key, "Content-Type": "application/json"} if key else {"Content-Type": "application/json"}

# Link roofing_agent to prompt_id=1 (the Aisha prompt)
r = httpx.post(base + "/dashboard/agents", headers=h, json={
    "slug": "roofing_agent",
    "opening_line": "Hello, this is Aisha from Sambhav Tech. Am I speaking with the owner of {business_name}?",
    "is_active": True,
    "prompt_id": 1,
}, timeout=15)
print("Update roofing_agent prompt_id=1:", r.status_code, r.text)

# Verify
r2 = httpx.get(base + "/dashboard/agents", headers=h, timeout=15)
agents = r2.json()
for a in agents:
    slug = a["slug"]
    pid = a.get("prompt_id")
    opening = a["opening_line"][:60]
    print(f"  {slug}: prompt_id={pid}, opening={opening}...")
