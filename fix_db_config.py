"""Fix DB configuration issues:
1. Fix ai_config tts_model from 'tts-1' to 'bulbul:v3'
2. Fix agent opening_line to use 'Aisha' instead of 'Sam'
"""
import os
import httpx
from dotenv import load_dotenv
load_dotenv()

base = os.getenv("API_BASE_URL", "https://livekit-outbound-api.tinysaas.fun")
key = os.getenv("API_SECRET_KEY", "")
headers = {"x-api-key": key, "Content-Type": "application/json"} if key else {"Content-Type": "application/json"}

# 1. Fix AI config: tts_model should be bulbul:v3, not tts-1
print("=== Fixing AI Config ===")
r1 = httpx.post(f"{base}/dashboard/ai-configs", headers=headers, json={
    "name": "default_telephony_config",
    "llm_provider": "groq",
    "llm_model": "llama-3.3-70b-versatile",
    "llm_temperature": 0.7,
    "stt_provider": "deepgram",
    "stt_model": "nova-3",
    "stt_language": "en-US",
    "tts_provider": "sarvam",
    "tts_model": "bulbul:v3",
    "tts_voice": "niharika",
    "tts_language": "hi-IN",
    "tts_speed": 1.0,
    "is_active": True,
}, timeout=15)
print(f"AI Config update: {r1.status_code} {r1.text}")

# 2. Fix default_roofing_agent opening line (Sam -> Aisha)
print("\n=== Fixing Agent Opening Lines ===")

# We need to find the right API to update agent opening_line
# Check if there's a PATCH/PUT agent endpoint
r2 = httpx.get(f"{base}/dashboard/agents", headers=headers, timeout=15)
print(f"Current agents: {r2.text[:500]}")

# 3. Verify the fix
print("\n=== Verify AI Config ===")
r3 = httpx.get(f"{base}/dashboard/ai-config", headers=headers, timeout=15)
print(r3.text)
