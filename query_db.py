"""Temporary script to query DB config."""
import os
import subprocess
subprocess.run(["pip", "install", "psycopg2-binary", "-q"], check=False)

from dotenv import load_dotenv
load_dotenv()

import psycopg2

url = os.getenv("NEON_DATABASE_URL")
conn = psycopg2.connect(url)
cur = conn.cursor()

# 1. ai_configs
cur.execute("SELECT name, llm_provider, llm_model, tts_provider, tts_model, tts_voice, is_active FROM ai_configs ORDER BY name")
cols = [d[0] for d in cur.description]
print("=== AI CONFIGS ===")
for row in cur.fetchall():
    print(dict(zip(cols, row)))

# 2. agents
cur.execute("SELECT slug, ai_config_name, prompt_id, opening_line FROM agents ORDER BY slug")
cols = [d[0] for d in cur.description]
print("\n=== AGENTS ===")
for row in cur.fetchall():
    print(dict(zip(cols, row)))

# 3. prompts (first 500 chars)
cur.execute("SELECT id, name, is_active, LEFT(content, 500) as preview FROM prompts WHERE is_active = true ORDER BY name")
cols = [d[0] for d in cur.description]
print("\n=== ACTIVE PROMPTS ===")
for row in cur.fetchall():
    print(dict(zip(cols, row)))

conn.close()
