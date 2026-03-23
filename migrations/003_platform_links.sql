-- Migration: Link prompts & AI configs to agents; add agent_slug to objections
-- Run this against your Neon PostgreSQL database

-- 1. Add prompt_id FK column to agent_configs
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='prompt_id') THEN
        ALTER TABLE agent_configs ADD COLUMN prompt_id INTEGER REFERENCES prompts(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 2. Add ai_config_name column to agent_configs
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='ai_config_name') THEN
        ALTER TABLE agent_configs ADD COLUMN ai_config_name TEXT;
    END IF;
END $$;

-- 3. Add agent_slug column to objections
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='objections' AND column_name='agent_slug') THEN
        ALTER TABLE objections ADD COLUMN agent_slug TEXT;
        CREATE INDEX idx_objections_agent_slug ON objections(agent_slug);
    END IF;
END $$;

-- 4. Ensure ai_configs has a unique constraint on name for upsert
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE tablename = 'ai_configs' AND indexname = 'ai_configs_name_key'
    ) THEN
        -- Only add if not already unique
        BEGIN
            ALTER TABLE ai_configs ADD CONSTRAINT ai_configs_name_key UNIQUE (name);
        EXCEPTION WHEN duplicate_table THEN
            -- Constraint already exists
            NULL;
        END;
    END IF;
END $$;
