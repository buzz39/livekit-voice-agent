# Neon Database Integration

## Overview
Your LiveKit telephony agent now uses Neon PostgreSQL to store prompts, contacts, and call logs. This allows you to update agent instructions without redeploying.

## Database Schema

### Tables Created

1. **prompts** - Store agent instructions
   - `id` - Primary key
   - `name` - Unique prompt name (e.g., "default_roofing_agent")
   - `content` - Full agent instructions text
   - `version` - Version number
   - `is_active` - Whether this prompt is currently active
   - `created_at`, `updated_at` - Timestamps

2. **contacts** - Lead database
   - `id` - Primary key
   - `phone_number` - Unique phone number
   - `business_name` - Company name
   - `contact_name` - Person's name
   - `email` - Email address
   - `interest_level` - Hot, Warm, Cold, No Interest
   - `created_at`, `updated_at` - Timestamps

3. **calls** - Call logs
   - `id` - Primary key
   - `contact_id` - Foreign key to contacts
   - `room_id` - LiveKit room ID
   - `prompt_id` - Which prompt was used
   - `duration_seconds` - Call length
   - `interest_level` - Outcome
   - `objection` - Any objections raised
   - `notes` - Additional notes
   - `email_captured` - Boolean
   - `demo_sent` - Boolean
   - `call_status` - completed, failed, etc.
   - `created_at` - Timestamp

4. **campaigns** - Campaign management
   - `id` - Primary key
   - `name` - Campaign name
   - `prompt_id` - Which prompt to use
   - `target_industry` - Industry focus
   - `is_active` - Boolean
   - `created_at` - Timestamp

5. **objections** - Track common objections
   - `id` - Primary key
   - `objection_text` - The objection
   - `response_text` - How to respond
   - `frequency` - How often it occurs
   - `created_at`, `updated_at` - Timestamps

6. **ai_configs** - AI provider configurations
   - `id` - Primary key
   - `name` - Unique config name (e.g., "default_telephony_config")
   - `llm_provider` - LLM provider (openai, etc.)
   - `llm_model` - Model name (gpt-4o-mini, etc.)
   - `llm_temperature` - Temperature setting (0.0-1.0)
   - `stt_provider` - Speech-to-text provider (deepgram, etc.)
   - `stt_model` - STT model name (nova-3, etc.)
   - `stt_language` - Language code (en-US, etc.)
   - `tts_provider` - Text-to-speech provider (cartesia, etc.)
   - `tts_model` - TTS model name (sonic-2, etc.)
   - `tts_voice` - Voice ID
   - `tts_language` - Language code (en, etc.)
   - `tts_speed` - Speech speed (0.5-2.0)
   - `is_active` - Boolean
   - `created_at`, `updated_at` - Timestamps

## How It Works

### 1. Agent Fetches Prompt on Startup
```python
# Agent loads instructions from database instead of file
agent_instructions = await db.get_active_prompt("default_roofing_agent")
```

### 2. Contact Created/Updated
```python
# Each call creates or updates contact
contact_id = await db.upsert_contact(
    phone_number=phone_number,
    business_name=business_name
)
```

### 3. Call Logged After Completion
```python
# Call details saved to database
await db.log_call(
    contact_id=contact_id,
    room_id=ctx.room.name,
    duration_seconds=call_duration
)
```

## Setting Up the Database

### Create the AI Config Table
Run the SQL script to create the new table:
```bash
psql $NEON_DATABASE_URL -f create_ai_config_table.sql
```

Or run directly in Neon Console:
```sql
-- See create_ai_config_table.sql for full schema
```

## Updating AI Configuration

### Change LLM Model
```sql
UPDATE ai_configs 
SET llm_model = 'gpt-4o',
    llm_temperature = 0.8,
    updated_at = NOW()
WHERE name = 'default_telephony_config';
```

### Change TTS Voice
```sql
UPDATE ai_configs 
SET tts_voice = 'new-voice-id-here',
    tts_speed = 1.1,
    updated_at = NOW()
WHERE name = 'default_telephony_config';
```

### Change STT Language
```sql
UPDATE ai_configs 
SET stt_language = 'es-US',
    updated_at = NOW()
WHERE name = 'default_telephony_config';
```

## Updating Agent Instructions

### Option 1: Direct SQL (Neon Console)
```sql
UPDATE prompts 
SET content = 'Your new agent instructions here...',
    version = version + 1,
    updated_at = NOW()
WHERE name = 'default_roofing_agent';
```

### Option 2: Python Script
```python
import asyncio
from neon_db import get_db

async def update_prompt():
    db = await get_db()
    
    new_instructions = """
    Your updated agent instructions here...
    """
    
    await db.pool.execute("""
        UPDATE prompts 
        SET content = $1, version = version + 1, updated_at = NOW()
        WHERE name = $2
    """, new_instructions, "default_roofing_agent")
    
    print("Prompt updated!")

asyncio.run(update_prompt())
```

### Option 3: Build a Dashboard
Create a web interface to manage prompts, view call logs, and track analytics.

## Querying Call Data

### Get Recent Calls
```sql
SELECT 
    c.created_at,
    co.business_name,
    co.phone_number,
    c.interest_level,
    c.duration_seconds,
    c.email_captured
FROM calls c
JOIN contacts co ON c.contact_id = co.id
ORDER BY c.created_at DESC
LIMIT 50;
```

### Conversion Rate
```sql
SELECT 
    COUNT(*) as total_calls,
    COUNT(CASE WHEN interest_level = 'Hot' THEN 1 END) as hot_leads,
    COUNT(CASE WHEN email_captured = true THEN 1 END) as emails_captured,
    ROUND(100.0 * COUNT(CASE WHEN email_captured = true THEN 1 END) / COUNT(*), 2) as conversion_rate
FROM calls
WHERE created_at > NOW() - INTERVAL '7 days';
```

### Top Objections
```sql
SELECT 
    objection_text,
    frequency,
    response_text
FROM objections
ORDER BY frequency DESC
LIMIT 10;
```

## Connection Details

**Project:** livekit  
**Database:** neondb  
**Region:** us-east-1 (AWS)  
**Connection String:** Stored in `.env` as `NEON_DATABASE_URL`

## Next Steps

1. **Test the integration** - Make a test call and verify data is logged
2. **Update a prompt** - Try changing the agent instructions via SQL
3. **Build analytics** - Query call data to track performance
4. **Create dashboard** - Build a web UI for managing prompts and viewing stats
5. **A/B testing** - Create multiple prompts and compare conversion rates

## Neon Console Access

Visit: https://console.neon.tech/app/projects/red-waterfall-71608110

You can:
- Run SQL queries directly
- View table data
- Monitor database performance
- Create branches for testing schema changes
