# AI Configuration Management

Your telephony agent now reads LLM, TTS, and STT configurations from the Neon database, allowing you to change AI providers and models without redeploying your code.

## Quick Start

### 1. Create the Database Table

Run the SQL script to set up the `ai_configs` table:

```bash
psql $NEON_DATABASE_URL -f create_ai_config_table.sql
```

Or execute the SQL directly in the [Neon Console](https://console.neon.tech).

### 2. Update Configuration

Use the helper script to update settings:

```bash
# Change LLM model
python update_ai_config.py --llm-model gpt-4o

# Change TTS voice and speed
python update_ai_config.py --tts-voice "new-voice-id" --tts-speed 1.2

# Change STT language to Spanish
python update_ai_config.py --stt-language es-US

# Update multiple settings at once
python update_ai_config.py --llm-temperature 0.8 --tts-speed 1.1
```

### 3. Restart Your Agent

The agent reads configuration on startup, so restart it to apply changes:

```bash
python telephony_agent.py dev
```

## Configuration Options

### LLM (Language Model)
- **Provider**: `openai` (more providers can be added)
- **Model**: `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`
- **Temperature**: `0.0` (deterministic) to `1.0` (creative)

### STT (Speech-to-Text)
- **Provider**: `deepgram` (more providers can be added)
- **Model**: `nova-3`, `nova-2`, `base`
- **Language**: `en-US`, `es-US`, `fr-FR`, etc.

### TTS (Text-to-Speech)
- **Provider**: `cartesia` (more providers can be added)
- **Model**: `sonic-2`, `sonic-1`
- **Voice**: Voice ID from provider
- **Language**: `en`, `es`, `fr`, etc.
- **Speed**: `0.5` (slow) to `2.0` (fast)

## Direct SQL Updates

You can also update configurations directly via SQL:

```sql
-- Change to GPT-4o with higher temperature
UPDATE ai_configs 
SET llm_model = 'gpt-4o',
    llm_temperature = 0.8,
    updated_at = NOW()
WHERE name = 'default_telephony_config';

-- Switch to Spanish
UPDATE ai_configs 
SET stt_language = 'es-US',
    tts_language = 'es',
    updated_at = NOW()
WHERE name = 'default_telephony_config';

-- Adjust TTS speed
UPDATE ai_configs 
SET tts_speed = 1.2,
    updated_at = NOW()
WHERE name = 'default_telephony_config';
```

## View Current Configuration

```sql
SELECT * FROM ai_configs WHERE name = 'default_telephony_config';
```

## Multiple Configurations

You can create multiple configurations for different use cases:

```sql
-- Create a Spanish-language configuration
INSERT INTO ai_configs (
    name, llm_model, stt_language, tts_language
) VALUES (
    'spanish_config', 'gpt-4o-mini', 'es-US', 'es'
);

-- Create a high-quality configuration
INSERT INTO ai_configs (
    name, llm_model, llm_temperature, tts_model
) VALUES (
    'premium_config', 'gpt-4o', 0.9, 'sonic-2'
);
```

Then modify your code to use different configs based on context:

```python
# In telephony_agent.py
config_name = "spanish_config" if is_spanish_call else "default_telephony_config"
ai_config = await db.get_ai_config(config_name)
```

## Adding New Providers

To add support for new AI providers:

1. Update the database with the new provider name
2. Add the provider initialization code in `telephony_agent.py`
3. Install any required packages

Example for adding Azure OpenAI:

```python
# In telephony_agent.py
if ai_config["llm_provider"] == "azure":
    from livekit.plugins import azure
    llm = azure.LLM(
        model=ai_config["llm_model"],
        temperature=float(ai_config["llm_temperature"])
    )
```

## Best Practices

1. **Test changes** - Always test configuration changes with a test call first
2. **Monitor costs** - Different models have different pricing
3. **Track performance** - Log which config was used for each call
4. **Version control** - Keep track of config changes in your database
5. **Fallback defaults** - The code includes fallback values if database is unavailable

## Troubleshooting

### Configuration not loading
- Check database connection: `psql $NEON_DATABASE_URL -c "SELECT * FROM ai_configs;"`
- Verify `is_active = true` for your configuration
- Check agent logs for database errors

### Unsupported provider warning
- The agent will fall back to defaults if it doesn't recognize a provider
- Add support for the provider in `telephony_agent.py`

### Changes not taking effect
- Remember to restart the agent after updating configuration
- Configuration is loaded once at startup, not dynamically
