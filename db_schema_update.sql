-- Database Schema Update for SaaS Frontend
-- Adds support for multi-tenancy and agent configuration

-- 1. Agent Configurations
CREATE TABLE IF NOT EXISTS agent_configs (
    slug TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL, -- Stack Auth User ID
    opening_line TEXT,
    mcp_endpoint_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Webhook Configurations
CREATE TABLE IF NOT EXISTS webhook_configs (
    id SERIAL PRIMARY KEY,
    slug TEXT NOT NULL, -- Link to agent
    event_type TEXT NOT NULL, -- e.g., 'call.completed', 'lead.captured'
    target_url TEXT NOT NULL,
    headers JSONB DEFAULT '{}'::JSONB,
    is_active BOOLEAN DEFAULT true,
    owner_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Data Collection Schemas
CREATE TABLE IF NOT EXISTS data_schemas (
    id SERIAL PRIMARY KEY,
    slug TEXT NOT NULL, -- Link to agent
    field_name TEXT NOT NULL, -- e.g., 'roof_age'
    description TEXT, -- For the AI prompt
    field_type TEXT DEFAULT 'string', -- string, number, boolean, date
    validation_rules JSONB,
    owner_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Add owner_id to existing tables for multi-tenancy
-- We use DO blocks to safely add columns if they don't exist

DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prompts' AND column_name='owner_id') THEN
        ALTER TABLE prompts ADD COLUMN owner_id TEXT;
        CREATE INDEX idx_prompts_owner ON prompts(owner_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='contacts' AND column_name='owner_id') THEN
        ALTER TABLE contacts ADD COLUMN owner_id TEXT;
        CREATE INDEX idx_contacts_owner ON contacts(owner_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='calls' AND column_name='owner_id') THEN
        ALTER TABLE calls ADD COLUMN owner_id TEXT;
        CREATE INDEX idx_calls_owner ON calls(owner_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ai_configs' AND column_name='owner_id') THEN
        ALTER TABLE ai_configs ADD COLUMN owner_id TEXT;
        CREATE INDEX idx_ai_configs_owner ON ai_configs(owner_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='objections' AND column_name='owner_id') THEN
        ALTER TABLE objections ADD COLUMN owner_id TEXT;
    END IF;
END $$;

-- Fix: replace invalid model name 'gpt-5-nano' with working Groq model
UPDATE ai_configs
SET llm_model = 'llama-3.3-70b-versatile',
    llm_provider = 'groq'
WHERE llm_model = 'gpt-5-nano';

-- Fix: replace legacy Sarvam values that cause 400 Bad Request responses
UPDATE ai_configs
SET tts_voice = 'anushka'
WHERE tts_provider = 'sarvam'
    AND LOWER(COALESCE(tts_voice, '')) IN ('sarah', 'meera');

UPDATE ai_configs
SET tts_model = 'bulbul:v1'
WHERE tts_provider = 'sarvam'
    AND COALESCE(tts_model, '') IN ('', 'sarvam');
