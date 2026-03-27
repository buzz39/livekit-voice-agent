"""Check prompt for gendered references."""
import os, re, httpx
from dotenv import load_dotenv
load_dotenv()

base = os.getenv("API_BASE_URL", "https://livekit-outbound-api.tinysaas.fun")
key = os.getenv("API_SECRET_KEY", "")
headers = {"x-api-key": key} if key else {}

r = httpx.get(f"{base}/dashboard/prompt/2", headers=headers, timeout=15)
data = r.json()
content = data.get("content", "")

for match in re.finditer(r"(?i)(sam|he |his |him |she |her |aisha|male|female|man |woman)", content):
    start = max(0, match.start() - 40)
    end = min(len(content), match.end() + 40)
    snippet = content[start:end].replace("\n", " ")
    print(f"  [{match.start()}] '{match.group().strip()}' -> ...{snippet}...")
