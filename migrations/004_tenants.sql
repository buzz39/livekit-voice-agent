-- Migration: add tenant configuration storage
-- Run this against your Neon PostgreSQL database

CREATE TABLE IF NOT EXISTS tenant_configs (
    tenant_id TEXT PRIMARY KEY,
    display_name TEXT,
    agent_slug TEXT,
    workflow_policy TEXT,
    routing_policy JSONB DEFAULT '{}'::JSONB,
    ai_overrides JSONB DEFAULT '{}'::JSONB,
    opening_line TEXT,
    api_key TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenant_configs_is_active ON tenant_configs(is_active);
