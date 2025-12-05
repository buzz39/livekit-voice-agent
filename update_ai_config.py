"""
Helper script to update AI configuration in Neon database

Usage:
    python update_ai_config.py --llm-model gpt-4o
    python update_ai_config.py --tts-voice new-voice-id --tts-speed 1.2
    python update_ai_config.py --stt-language es-US
"""

import asyncio
import argparse
from neon_db import get_db

async def update_config(args):
    """Update AI configuration based on command line arguments."""
    db = await get_db()
    
    updates = []
    params = []
    param_count = 1
    
    if args.llm_provider:
        updates.append(f"llm_provider = ${param_count}")
        params.append(args.llm_provider)
        param_count += 1
    
    if args.llm_model:
        updates.append(f"llm_model = ${param_count}")
        params.append(args.llm_model)
        param_count += 1
    
    if args.llm_temperature is not None:
        updates.append(f"llm_temperature = ${param_count}")
        params.append(args.llm_temperature)
        param_count += 1
    
    if args.stt_provider:
        updates.append(f"stt_provider = ${param_count}")
        params.append(args.stt_provider)
        param_count += 1
    
    if args.stt_model:
        updates.append(f"stt_model = ${param_count}")
        params.append(args.stt_model)
        param_count += 1
    
    if args.stt_language:
        updates.append(f"stt_language = ${param_count}")
        params.append(args.stt_language)
        param_count += 1
    
    if args.tts_provider:
        updates.append(f"tts_provider = ${param_count}")
        params.append(args.tts_provider)
        param_count += 1
    
    if args.tts_model:
        updates.append(f"tts_model = ${param_count}")
        params.append(args.tts_model)
        param_count += 1
    
    if args.tts_voice:
        updates.append(f"tts_voice = ${param_count}")
        params.append(args.tts_voice)
        param_count += 1
    
    if args.tts_language:
        updates.append(f"tts_language = ${param_count}")
        params.append(args.tts_language)
        param_count += 1
    
    if args.tts_speed is not None:
        updates.append(f"tts_speed = ${param_count}")
        params.append(args.tts_speed)
        param_count += 1
    
    if not updates:
        print("No updates specified. Use --help to see available options.")
        return
    
    updates.append("updated_at = NOW()")
    params.append(args.config_name)
    
    query = f"""
        UPDATE ai_configs 
        SET {', '.join(updates)}
        WHERE name = ${param_count}
    """
    
    async with db.pool.acquire() as conn:
        result = await conn.execute(query, *params)
        
    if "UPDATE 1" in result:
        print(f"✓ Configuration '{args.config_name}' updated successfully!")
        
        # Show current config
        config = await db.get_ai_config(args.config_name)
        if config:
            print("\nCurrent configuration:")
            print(f"  LLM: {config['llm_provider']}/{config['llm_model']} (temp: {config['llm_temperature']})")
            print(f"  STT: {config['stt_provider']}/{config['stt_model']} ({config['stt_language']})")
            print(f"  TTS: {config['tts_provider']}/{config['tts_model']} (speed: {config['tts_speed']})")
    else:
        print(f"✗ Configuration '{args.config_name}' not found.")
    
    await db.close()

def main():
    parser = argparse.ArgumentParser(description="Update AI configuration in Neon database")
    
    parser.add_argument("--config-name", default="default_telephony_config",
                       help="Configuration name (default: default_telephony_config)")
    
    # LLM options
    parser.add_argument("--llm-provider", help="LLM provider (e.g., openai)")
    parser.add_argument("--llm-model", help="LLM model (e.g., gpt-4o-mini, gpt-4o)")
    parser.add_argument("--llm-temperature", type=float, help="LLM temperature (0.0-1.0)")
    
    # STT options
    parser.add_argument("--stt-provider", help="STT provider (e.g., deepgram)")
    parser.add_argument("--stt-model", help="STT model (e.g., nova-3)")
    parser.add_argument("--stt-language", help="STT language (e.g., en-US, es-US)")
    
    # TTS options
    parser.add_argument("--tts-provider", help="TTS provider (e.g., cartesia)")
    parser.add_argument("--tts-model", help="TTS model (e.g., sonic-2)")
    parser.add_argument("--tts-voice", help="TTS voice ID")
    parser.add_argument("--tts-language", help="TTS language (e.g., en, es)")
    parser.add_argument("--tts-speed", type=float, help="TTS speed (0.5-2.0)")
    
    args = parser.parse_args()
    asyncio.run(update_config(args))

if __name__ == "__main__":
    main()
