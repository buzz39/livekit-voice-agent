"""
Neon Database Integration for LiveKit Telephony Agent

Handles:
- Fetching agent prompts from database
- Logging call results
- Managing contacts and leads
"""

import os
import logging
import json
from typing import Optional, Dict, Any, List, Union
import asyncpg
from datetime import datetime, timedelta

logger = logging.getLogger("neon-db")

class NeonDB:
    """Neon PostgreSQL database client for telephony agent."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize with connection string from env or parameter."""
        self.connection_string = connection_string or os.environ.get("NEON_DATABASE_URL", "")
        if not self.connection_string:
            raise ValueError("NEON_DATABASE_URL environment variable is not set")
        self.pool = None
    
    async def connect(self):
        """Create connection pool."""
        if not self.connection_string:
            raise ValueError("NEON_DATABASE_URL not set")
        
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        logger.info("Connected to Neon database")
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Closed Neon database connection")
    
    async def get_active_prompt(self, name: str = "default_roofing_agent") -> Optional[str]:
        """Fetch active prompt content by name."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT content FROM prompts WHERE name = $1 AND is_active = true",
                name
            )
            return row["content"] if row else None

    async def get_all_prompts(self, industry: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all available prompts, optionally filtered by industry."""
        async with self.pool.acquire() as conn:
            if industry:
                rows = await conn.fetch(
                    "SELECT id, name, industry, description, is_active, created_at, updated_at FROM prompts WHERE industry = $1 ORDER BY name",
                    industry,
                )
            else:
                rows = await conn.fetch(
                    "SELECT id, name, industry, description, is_active, created_at, updated_at FROM prompts ORDER BY industry, name"
                )
            result = []
            for row in rows:
                d = dict(row)
                for key in ("created_at", "updated_at"):
                    if d.get(key):
                        d[key] = d[key].isoformat()
                result.append(d)
            return result

    async def get_prompt_by_id(self, prompt_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single prompt by ID with full content."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, content, industry, description, is_active, created_at, updated_at FROM prompts WHERE id = $1",
                prompt_id,
            )
            if not row:
                return None
            d = dict(row)
            for key in ("created_at", "updated_at"):
                if d.get(key):
                    d[key] = d[key].isoformat()
            return d

    async def create_prompt(self, name: str, content: str, industry: str = "general", description: str = "", is_active: bool = True) -> int:
        """Create a new prompt and return its ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO prompts (name, content, industry, description, is_active)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, name, content, industry, description, is_active)
            return row["id"]

    async def update_prompt(self, prompt_id: int, name: Optional[str] = None, content: Optional[str] = None, industry: Optional[str] = None, description: Optional[str] = None, is_active: Optional[bool] = None):
        """Update a prompt by ID. Only provided fields are changed."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE prompts
                SET name        = COALESCE($2, name),
                    content     = COALESCE($3, content),
                    industry    = COALESCE($4, industry),
                    description = COALESCE($5, description),
                    is_active   = COALESCE($6, is_active),
                    updated_at  = NOW()
                WHERE id = $1
            """, prompt_id, name, content, industry, description, is_active)

    async def delete_prompt(self, prompt_id: int):
        """Delete a prompt by ID."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM prompts WHERE id = $1", prompt_id)

    async def get_industries(self) -> List[str]:
        """Return distinct industry values from prompts table."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT industry FROM prompts WHERE industry IS NOT NULL ORDER BY industry")
            return [row["industry"] for row in rows]

    async def clone_prompt(self, prompt_id: int, new_name: str, new_industry: str) -> int:
        """Clone an existing prompt into a new industry/name."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT content, description FROM prompts WHERE id = $1",
                prompt_id,
            )
            if not row:
                raise ValueError("Source prompt not found")
            new_id = await conn.fetchval("""
                INSERT INTO prompts (name, content, industry, description, is_active)
                VALUES ($1, $2, $3, $4, true)
                RETURNING id
            """, new_name, row["content"], new_industry, row["description"])
            return new_id

    async def update_active_prompt(self, name: str, content: str):
        """Update active prompt content."""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    UPDATE prompts
                    SET content = $2, updated_at = NOW()
                    WHERE name = $1 AND is_active = true
                """, name, content)
            except asyncpg.UndefinedColumnError:
                await conn.execute("""
                    UPDATE prompts
                    SET content = $2
                    WHERE name = $1 AND is_active = true
                """, name, content)

    async def upsert_contact(
        self,
        phone_number: str,
        business_name: Optional[str] = None,
        contact_name: Optional[str] = None,
        email: Optional[str] = None,
        interest_level: Optional[str] = None
    ) -> int:
        """Insert or update contact, return contact_id."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO contacts (phone_number, business_name, contact_name, email, interest_level)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (phone_number) 
                DO UPDATE SET
                    business_name = COALESCE(EXCLUDED.business_name, contacts.business_name),
                    contact_name = COALESCE(EXCLUDED.contact_name, contacts.contact_name),
                    email = COALESCE(EXCLUDED.email, contacts.email),
                    interest_level = COALESCE(EXCLUDED.interest_level, contacts.interest_level),
                    updated_at = NOW()
                RETURNING id
            """, phone_number, business_name, contact_name, email, interest_level)
            return row["id"]

    async def update_contact_email(self, contact_id: Union[int, str], email: str):
        """Update contact email."""
        if isinstance(contact_id, str) and contact_id.isdigit():
            contact_id = int(contact_id)

        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE contacts
                SET email = $2, updated_at = NOW()
                WHERE id = $1
            """, contact_id, email)
    
    async def get_data_schema(self, slug: str = "default_roofing_agent") -> List[Dict[str, Any]]:
        """Fetch data schema for the agent."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT field_name, field_type, description, validation_rules FROM data_schemas WHERE slug = $1",
                slug
            )
            return [dict(row) for row in rows]
            
    async def log_call(
        self,
        contact_id: int,
        room_id: str,
        prompt_id: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        interest_level: Optional[str] = None,
        objection: Optional[str] = None,
        notes: Optional[str] = None,
        email_captured: bool = False,
        call_status: str = "completed",
        transcript: Optional[str] = None,
        captured_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Log call details, return call_id."""
        async with self.pool.acquire() as conn:
            # Safe JSON serialization
            try:
                json_data = json.dumps(captured_data) if captured_data else '{}'
            except TypeError as e:
                logger.error(f"Failed to serialize captured_data in log_call: {e}")
                json_data = '{}'
            
            row = await conn.fetchrow("""
                INSERT INTO calls (
                    contact_id, room_id, prompt_id, duration_seconds,
                    interest_level, objection, notes, email_captured, call_status,
                    transcript, captured_data
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """, contact_id, room_id, prompt_id, duration_seconds,
                interest_level, objection, notes, email_captured, call_status, transcript, json_data)
            return row["id"]

    async def update_call(
        self,
        call_id: int,
        duration_seconds: Optional[int] = None,
        interest_level: Optional[str] = None,
        objection: Optional[str] = None,
        notes: Optional[str] = None,
        email_captured: bool = False,
        call_status: str = "completed",
        transcript: Optional[str] = None,
        captured_data: Optional[Dict[str, Any]] = None,
        recording_url: Optional[str] = None
    ):
        """Update an existing call record."""
        async with self.pool.acquire() as conn:
            # Safe JSON serialization
            try:
                # If captured_data is explicitly None, we want to preserve existing data.
                # But here we are passing it to COALESCE.
                # However, json.dumps(None) is 'null', not None.
                # If captured_data is None, we want $9 to be NULL so COALESCE picks the existing value.
                json_data = json.dumps(captured_data) if captured_data is not None else None
            except TypeError as e:
                logger.error(f"Failed to serialize captured_data for call {call_id}: {e}")
                # Log what we tried to serialize (truncated)
                try:
                    logger.debug(f"captured_data (truncated): {str(captured_data)[:1000]}")
                except:
                    pass
                json_data = None # Fallback to not updating it

            try:
                await conn.execute("""
                    UPDATE calls
                    SET
                        duration_seconds = COALESCE($2, duration_seconds),
                        interest_level = COALESCE($3, interest_level),
                        objection = COALESCE($4, objection),
                        notes = COALESCE($5, notes),
                        email_captured = COALESCE($6, email_captured),
                        call_status = COALESCE($7, call_status),
                        transcript = COALESCE($8, transcript),
                        captured_data = COALESCE($9, captured_data),
                        recording_url = COALESCE($10, recording_url)
                    WHERE id = $1
                """, call_id, duration_seconds, interest_level, objection, notes,
                     email_captured, call_status, transcript, json_data, recording_url)
            except Exception as e:
                logger.error(f"DB Update failed for call {call_id}: {e}")
                raise e
    
    async def update_call_recording(self, room_id: str, recording_url: str, call_id: Optional[int] = None):
        """Update the recording URL for a call."""
        async with self.pool.acquire() as conn:
            if call_id:
                # Targeted update by ID (preferred)
                await conn.execute("""
                    UPDATE calls
                    SET recording_url = $2
                    WHERE id = $1
                """, call_id, recording_url)
            else:
                # Legacy: update by room_id (may affect multiple rows if room_id is reused)
                await conn.execute("""
                    UPDATE calls
                    SET recording_url = $2
                    WHERE room_id = $1
                """, room_id, recording_url)

    async def get_prompt_id(self, name: str = "default_roofing_agent") -> Optional[int]:
        """Get prompt ID by name."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM prompts WHERE name = $1 AND is_active = true",
                name
            )
            return row["id"] if row else None
    
    async def track_objection(self, objection_text: str, response_text: Optional[str] = None):
        """Track or increment objection frequency."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO objections (objection_text, response_text, frequency)
                VALUES ($1, $2, 1)
                ON CONFLICT (objection_text)
                DO UPDATE SET
                    frequency = objections.frequency + 1,
                    response_text = COALESCE(EXCLUDED.response_text, objections.response_text),
                    updated_at = NOW()
            """, objection_text, response_text)

    async def get_all_objections(self, agent_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all objection handlers, optionally filtered by agent_slug."""
        async with self.pool.acquire() as conn:
            if agent_slug:
                rows = await conn.fetch("""
                    SELECT id, objection_text, response_text, frequency, agent_slug, created_at, updated_at
                    FROM objections WHERE agent_slug = $1 ORDER BY frequency DESC
                """, agent_slug)
            else:
                rows = await conn.fetch("""
                    SELECT id, objection_text, response_text, frequency, agent_slug, created_at, updated_at
                    FROM objections ORDER BY frequency DESC
                """)
            result = []
            for row in rows:
                d = dict(row)
                for key in ("created_at", "updated_at"):
                    if d.get(key):
                        d[key] = d[key].isoformat()
                result.append(d)
            return result

    async def upsert_objection(self, objection_text: str, response_text: str = "", agent_slug: Optional[str] = None):
        """Create or update an objection handler with response."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO objections (objection_text, response_text, agent_slug, frequency)
                VALUES ($1, $2, $3, 0)
                ON CONFLICT (objection_text)
                DO UPDATE SET
                    response_text = EXCLUDED.response_text,
                    agent_slug = COALESCE(EXCLUDED.agent_slug, objections.agent_slug),
                    updated_at = NOW()
            """, objection_text, response_text, agent_slug)

    async def delete_objection(self, objection_id: int):
        """Delete an objection by ID."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM objections WHERE id = $1", objection_id)
    
    async def get_call_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get call statistics for the last N days."""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_calls,
                    COUNT(CASE WHEN interest_level = 'Hot' THEN 1 END) as hot_leads,
                    COUNT(CASE WHEN interest_level = 'Warm' THEN 1 END) as warm_leads,
                    COUNT(CASE WHEN email_captured = true THEN 1 END) as emails_captured,
                    AVG(duration_seconds) as avg_duration
                FROM calls
                WHERE created_at > NOW() - make_interval(days := $1)
            """, days)
            return dict(stats) if stats else {}

    async def get_daily_call_volume(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily call volume for the last N days."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    to_char(created_at, 'YYYY-MM-DD') as date,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration,
                    COUNT(CASE WHEN call_status = 'completed' THEN 1 END) as completed,
                     COUNT(CASE WHEN call_status = 'failed' THEN 1 END) as failed
                FROM calls
                WHERE created_at > NOW() - make_interval(days := $1)
                GROUP BY 1
                ORDER BY 1 ASC
            """, days)
            return [dict(row) for row in rows]

    async def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent calls with contact details."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    c.id,
                    c.call_status,
                    c.duration_seconds,
                    c.created_at,
                    c.interest_level,
                    c.transcript,
                    c.recording_url,
                    con.contact_name,
                    con.phone_number,
                    con.business_name
                FROM calls c
                LEFT JOIN contacts con ON c.contact_id = con.id
                ORDER BY c.created_at DESC
                LIMIT $1
            """, limit)
            # Convert rows to dicts
            result = []
            for row in rows:
                row_dict = dict(row)
                if row_dict.get('created_at'):
                    row_dict['created_at'] = row_dict['created_at'].isoformat()
                result.append(row_dict)
            return result

    async def get_call(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a specific call by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    c.id,
                    c.call_status,
                    c.duration_seconds,
                    c.created_at,
                    c.interest_level,
                    c.transcript,
                    c.recording_url,
                    con.contact_name,
                    con.phone_number,
                    con.business_name
                FROM calls c
                LEFT JOIN contacts con ON c.contact_id = con.id
                WHERE c.id = $1
            """, call_id)
            if not row:
                return None
            row_dict = dict(row)
            if row_dict.get('created_at'):
                row_dict['created_at'] = row_dict['created_at'].isoformat()
            return row_dict
    
    async def get_webhooks(self, slug: str) -> List[Dict[str, Any]]:
        """Fetch active webhooks for the agent."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT event_type, target_url, headers 
                FROM webhook_configs 
                WHERE slug = $1 AND is_active = true
            """, slug)
            return [dict(row) for row in rows]
            
    async def get_agent_config(self, slug: str = "default-agent") -> Optional[Dict[str, Any]]:
        """Fetch agent configuration (greeting, MCP URL, prompt_id, ai_config_name)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT opening_line, mcp_endpoint_url, prompt_id, ai_config_name
                FROM agent_configs
                WHERE slug = $1 AND is_active = true
            """, slug)
            return dict(row) if row else None

    async def get_prompt_content_by_id(self, prompt_id: int) -> Optional[str]:
        """Fetch just the prompt content string by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT content FROM prompts WHERE id = $1 AND is_active = true",
                prompt_id,
            )
            return row["content"] if row else None

    async def get_ai_config(self, name: str = "default_telephony_config") -> Optional[Dict[str, Any]]:
        """Fetch AI configuration (LLM, TTS, STT, VAD) by name."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    llm_provider, llm_model, llm_temperature,
                    stt_provider, stt_model, stt_language,
                    tts_provider, tts_model, tts_voice, tts_language, tts_speed,
                    vad_silence_threshold, vad_sensitivity, vad_interruption_threshold
                FROM ai_configs 
                WHERE name = $1 AND is_active = true
            """, name)
            return dict(row) if row else None

    async def update_ai_config(
        self,
        name: str = "default_telephony_config",
        **kwargs: Any,
    ) -> None:
        """Update AI configuration fields by name.

        Only the provided keyword arguments are updated; the rest are left
        unchanged via COALESCE.  Supported keys mirror the ``ai_configs``
        columns: ``llm_provider``, ``llm_model``, ``tts_provider``,
        ``tts_language``, etc.
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE ai_configs
                SET
                    llm_provider   = COALESCE($2, llm_provider),
                    tts_provider   = COALESCE($3, tts_provider),
                    tts_language   = COALESCE($4, tts_language),
                    updated_at     = NOW()
                WHERE name = $1 AND is_active = true
            """, name, kwargs.get("llm_provider"), kwargs.get("tts_provider"), kwargs.get("tts_language"))
            # result is e.g. "UPDATE 1" or "UPDATE 0"
            if result and result.endswith("0"):
                logger.warning("update_ai_config: no active config row found for name=%s", name)

    async def get_all_ai_configs(self) -> List[Dict[str, Any]]:
        """Fetch all AI configurations."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT name,
                    llm_provider, llm_model, llm_temperature,
                    stt_provider, stt_model, stt_language,
                    tts_provider, tts_model, tts_voice, tts_language, tts_speed,
                    vad_silence_threshold, vad_sensitivity, vad_interruption_threshold,
                    is_active, created_at, updated_at
                FROM ai_configs ORDER BY name
            """)
            result = []
            for row in rows:
                d = dict(row)
                for key in ("created_at", "updated_at"):
                    if d.get(key):
                        d[key] = d[key].isoformat()
                result.append(d)
            return result

    async def upsert_ai_config_full(
        self,
        name: str,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o-mini",
        llm_temperature: float = 0.7,
        stt_provider: str = "deepgram",
        stt_model: str = "nova-3",
        stt_language: str = "en-US",
        tts_provider: str = "openai",
        tts_model: str = "tts-1",
        tts_voice: str = "alloy",
        tts_language: str = "",
        tts_speed: float = 1.0,
        vad_silence_threshold: float = 0.5,
        vad_sensitivity: float = 0.5,
        vad_interruption_threshold: float = 0.5,
        is_active: bool = True,
    ) -> str:
        """Create or update an AI configuration. Returns name."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ai_configs (name, llm_provider, llm_model, llm_temperature,
                    stt_provider, stt_model, stt_language,
                    tts_provider, tts_model, tts_voice, tts_language, tts_speed,
                    vad_silence_threshold, vad_sensitivity, vad_interruption_threshold, is_active)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                ON CONFLICT (name)
                DO UPDATE SET
                    llm_provider = EXCLUDED.llm_provider,
                    llm_model = EXCLUDED.llm_model,
                    llm_temperature = EXCLUDED.llm_temperature,
                    stt_provider = EXCLUDED.stt_provider,
                    stt_model = EXCLUDED.stt_model,
                    stt_language = EXCLUDED.stt_language,
                    tts_provider = EXCLUDED.tts_provider,
                    tts_model = EXCLUDED.tts_model,
                    tts_voice = EXCLUDED.tts_voice,
                    tts_language = EXCLUDED.tts_language,
                    tts_speed = EXCLUDED.tts_speed,
                    vad_silence_threshold = EXCLUDED.vad_silence_threshold,
                    vad_sensitivity = EXCLUDED.vad_sensitivity,
                    vad_interruption_threshold = EXCLUDED.vad_interruption_threshold,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
            """, name, llm_provider, llm_model, llm_temperature,
                stt_provider, stt_model, stt_language,
                tts_provider, tts_model, tts_voice, tts_language, tts_speed,
                vad_silence_threshold, vad_sensitivity, vad_interruption_threshold, is_active)
            return name

    # --- Agent Config CRUD ---

    async def get_all_agent_configs(self) -> List[Dict[str, Any]]:
        """Fetch all agent configurations."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT slug, owner_id, opening_line, mcp_endpoint_url, is_active, prompt_id, ai_config_name, created_at, updated_at
                FROM agent_configs ORDER BY slug
            """)
            result = []
            for row in rows:
                d = dict(row)
                for key in ("created_at", "updated_at"):
                    if d.get(key):
                        d[key] = d[key].isoformat()
                result.append(d)
            return result

    async def upsert_agent_config(self, slug: str, owner_id: str, opening_line: str = "", mcp_endpoint_url: str = "", is_active: bool = True, prompt_id: Optional[int] = None, ai_config_name: Optional[str] = None) -> str:
        """Create or update an agent configuration. Returns slug."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent_configs (slug, owner_id, opening_line, mcp_endpoint_url, is_active, prompt_id, ai_config_name)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (slug)
                DO UPDATE SET
                    opening_line = EXCLUDED.opening_line,
                    mcp_endpoint_url = EXCLUDED.mcp_endpoint_url,
                    is_active = EXCLUDED.is_active,
                    prompt_id = EXCLUDED.prompt_id,
                    ai_config_name = EXCLUDED.ai_config_name,
                    updated_at = NOW()
            """, slug, owner_id, opening_line, mcp_endpoint_url, is_active, prompt_id, ai_config_name)
            return slug

    async def delete_agent_config(self, slug: str):
        """Delete an agent configuration by slug."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_configs WHERE slug = $1", slug)

    # --- Data Schema CRUD ---

    async def get_all_data_schemas(self, slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch data schemas, optionally filtered by agent slug."""
        async with self.pool.acquire() as conn:
            if slug:
                rows = await conn.fetch(
                    "SELECT id, slug, field_name, field_type, description, validation_rules, created_at FROM data_schemas WHERE slug = $1 ORDER BY id",
                    slug,
                )
            else:
                rows = await conn.fetch("SELECT id, slug, field_name, field_type, description, validation_rules, created_at FROM data_schemas ORDER BY slug, id")
            result = []
            for row in rows:
                d = dict(row)
                if d.get("created_at"):
                    d["created_at"] = d["created_at"].isoformat()
                if d.get("validation_rules") and isinstance(d["validation_rules"], str):
                    try:
                        d["validation_rules"] = json.loads(d["validation_rules"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                result.append(d)
            return result

    async def create_data_schema_field(self, slug: str, field_name: str, field_type: str = "string", description: str = "", owner_id: str = "", validation_rules: Optional[Dict] = None) -> int:
        """Create a data schema field. Returns its ID."""
        async with self.pool.acquire() as conn:
            rules_json = json.dumps(validation_rules) if validation_rules else None
            row = await conn.fetchrow("""
                INSERT INTO data_schemas (slug, field_name, field_type, description, owner_id, validation_rules)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, slug, field_name, field_type, description, owner_id, rules_json)
            return row["id"]

    async def delete_data_schema_field(self, field_id: int):
        """Delete a data schema field by ID."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM data_schemas WHERE id = $1", field_id)


async def get_db() -> NeonDB:
    """Create a new database instance for each job."""
    # Always use NeonDB
    db = NeonDB()
    await db.connect()
    return db
