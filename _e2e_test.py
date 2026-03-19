"""Temporary E2E validation script — delete after testing."""
import os, sys

# Set env vars BEFORE any imports
os.environ['SARVAM_API_KEY'] = 'test-key'
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['DEEPGRAM_API_KEY'] = 'test-key'
os.environ['GROQ_API_KEY'] = 'test-key'
os.environ['CARTESIA_API_KEY'] = 'test-key'
os.environ['TTS_PROVIDER'] = 'sarvam'  # Override env-level setting for this test

# Debug: verify env vars are set
print(f"SARVAM_API_KEY set: {bool(os.getenv('SARVAM_API_KEY'))}")

from outbound.providers import _has_credentials, resolve_ai_configuration, build_tts, build_llm, build_stt

# Debug: check credential detection
print(f"_has_credentials('sarvam'): {_has_credentials('sarvam')}")

# Check if TTS_PROVIDER env var is overriding
print(f"TTS_PROVIDER env: {os.getenv('TTS_PROVIDER', 'NOT SET')}")

print("\n=== Step 1: resolve_ai_configuration ===")
r = resolve_ai_configuration(ai_config={
    'tts_provider': 'sarvam',
    'tts_voice': 'simran',
    'tts_language': 'hi-IN',
    'llm_provider': 'groq',
})
print(f"  tts_provider: {r['tts_provider']}")
print(f"  tts_model:    {r['tts_model']}")
print(f"  tts_voice:    {r['tts_voice']}")
print(f"  tts_language: {r['tts_language']}")

print("\n=== Step 2: build_tts (sarvam) ===")
try:
    tts = build_tts(ai_config={
        'tts_provider': 'sarvam',
        'tts_voice': 'simran',
        'tts_language': 'hi-IN',
    })
    print(f"  type: {type(tts).__module__}.{type(tts).__name__}")
    print(f"  sample_rate: {tts.sample_rate}")
    if hasattr(tts, '_opts'):
        opts = tts._opts
        for attr in ['speaker', 'model', 'target_language_code', 'speech_sample_rate']:
            if hasattr(opts, attr):
                print(f"  _opts.{attr} = {getattr(opts, attr)}")
    print("  TTS BUILD OK")
except Exception as e:
    print(f"  TTS BUILD FAILED: {e}")

print("\n=== Step 3: build_llm (groq) ===")
try:
    llm = build_llm(ai_config={'llm_provider': 'groq'})
    print(f"  type: {type(llm).__module__}.{type(llm).__name__}")
    print("  LLM BUILD OK")
except Exception as e:
    print(f"  LLM BUILD FAILED: {e}")

print("\n=== Step 4: build_stt (deepgram) ===")
try:
    stt = build_stt(ai_config={})
    print(f"  type: {type(stt).__module__}.{type(stt).__name__}")
    print("  STT BUILD OK")
except Exception as e:
    print(f"  STT BUILD FAILED: {e}")

print("\n=== ALL DONE ===")
