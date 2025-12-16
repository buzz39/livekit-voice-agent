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
        # Fallback to provided credentials if env var is not set (per user request)
        self.connection_string = connection_string or os.getenv("NEON_DATABASE_URL") or "postgresql://neondb_owner:npg_CnL8lfMaFcV1@ep-winter-base-a4mt71z2-pooler.us-east-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require"
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
    
    async def update_active_prompt(self, name: str, content: str):
        """Update active prompt content."""
        async with self.pool.acquire() as conn:
            # Check if updated_at column exists in prompts table, if not, skip it.
            # Assuming it exists based on other tables or just try-catch.
            # Standard practice is it exists.
            try:
                await conn.execute("""
                    UPDATE prompts
                    SET content = $2, updated_at = NOW()
                    WHERE name = $1 AND is_active = true
                """, name, content)
            except asyncpg.UndefinedColumnError:
                # Fallback if updated_at doesn't exist
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
        """Fetch agent configuration (greeting, MCP URL, etc)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT opening_line, mcp_endpoint_url
                FROM agent_configs
                WHERE slug = $1 AND is_active = true
            """, slug)
            return dict(row) if row else None

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


async def get_db() -> NeonDB:
    """Create a new database instance for each job."""
    # Always use NeonDB
    db = NeonDB()
    await db.connect()
    return db
