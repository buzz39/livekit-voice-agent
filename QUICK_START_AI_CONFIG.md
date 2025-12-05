# Quick Start: AI Configuration

## Setup (One-time)

```bash
# 1. Create the table
psql $NEON_DATABASE_URL -f create_ai_config_table.sql
```

## Common Updates

```bash
# Change to GPT-4o
python update_ai_config.py --llm-model gpt-4o

# Make agent speak faster
python update_ai_config.py --tts-speed 1.3

# Switch to Spanish
python update_ai_config.py --stt-language es-US --tts-language es

# Adjust creativity (temperature)
python update_ai_config.py --llm-temperature 0.9
```

## View Current Config

```bash
psql $NEON_DATABASE_URL -c "SELECT * FROM ai_configs WHERE name = 'default_telephony_config';"
```

## After Changes

```bash
# Restart agent to apply changes
python telephony_agent.py dev
```

That's it! Your agent now reads AI settings from the database.
