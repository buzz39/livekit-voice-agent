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
import aiosqlite
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
            json_data = json.dumps(captured_data) if captured_data else '{}'
            
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
    
    async def update_call_recording(self, room_id: str, recording_url: str):
        """Update the recording URL for a call."""
        async with self.pool.acquire() as conn:
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


class SQLiteDB:
    """SQLite fallback for local development."""
    def __init__(self, db_path: str = "local.db"):
        self.db_path = db_path
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self._init_schema()
        logger.info("Connected to SQLite database")

    async def close(self):
        if self.conn:
            await self.conn.close()
            logger.info("Closed SQLite database")

    async def _init_schema(self):
        """Initialize schema if not exists."""
        async with self.conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT UNIQUE,
                    business_name TEXT,
                    contact_name TEXT,
                    email TEXT,
                    interest_level TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER,
                    room_id TEXT,
                    prompt_id INTEGER,
                    duration_seconds INTEGER,
                    interest_level TEXT,
                    objection TEXT,
                    notes TEXT,
                    email_captured BOOLEAN,
                    call_status TEXT,
                    transcript TEXT,
                    captured_data TEXT,
                    recording_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(contact_id) REFERENCES contacts(id)
                )
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    content TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            await cur.execute("""
                 CREATE TABLE IF NOT EXISTS objections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    objection_text TEXT UNIQUE,
                    response_text TEXT,
                    frequency INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 )
            """)
            await self.conn.commit()

            # Seed data if empty
            await cur.execute("SELECT COUNT(*) FROM contacts")
            count = (await cur.fetchone())[0]
            if count == 0:
                await cur.execute("""
                    INSERT INTO contacts (phone_number, business_name, contact_name, email, interest_level)
                    VALUES
                    ('+15551234567', 'Acme Corp', 'John Doe', 'john@acme.com', 'Warm'),
                    ('+15559876543', 'Beta Industries', 'Jane Smith', 'jane@beta.com', 'Hot')
                """)
                # Seed calls
                await cur.execute("""
                    INSERT INTO calls (contact_id, duration_seconds, interest_level, call_status, transcript, created_at)
                    VALUES
                    (1, 120, 'Warm', 'completed', '[{"role": "agent", "text": "Hello"}, {"role": "user", "text": "Hi"}]', date('now', '-1 day')),
                    (2, 300, 'Hot', 'completed', '[{"role": "agent", "text": "Deal?"}, {"role": "user", "text": "Yes"}]', date('now', '-2 days'))
                """)
                await self.conn.commit()

    async def get_call_stats(self, days: int = 7) -> Dict[str, Any]:
        cursor = await self.conn.execute(f"""
            SELECT
                COUNT(*) as total_calls,
                COUNT(CASE WHEN interest_level = 'Hot' THEN 1 END) as hot_leads,
                COUNT(CASE WHEN interest_level = 'Warm' THEN 1 END) as warm_leads,
                COUNT(CASE WHEN email_captured = 1 THEN 1 END) as emails_captured,
                AVG(duration_seconds) as avg_duration
            FROM calls
            WHERE created_at > date('now', '-{days} days')
        """)
        row = await cursor.fetchone()
        return dict(row) if row else {}

    async def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = await self.conn.execute(f"""
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
            LIMIT {limit}
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_call(self, call_id: int) -> Optional[Dict[str, Any]]:
        cursor = await self.conn.execute("""
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
            WHERE c.id = ?
        """, (call_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # Implementing other methods as no-ops or simple mocks if needed for the UI to not crash
    async def get_active_prompt(self, name: str = "default_roofing_agent") -> Optional[str]:
        return "This is a mock prompt."

    async def upsert_contact(self, phone_number, business_name=None, contact_name=None, email=None, interest_level=None):
        async with self.conn.execute("""
            INSERT INTO contacts (phone_number, business_name, contact_name, email, interest_level)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(phone_number) DO UPDATE SET
            business_name=coalesce(excluded.business_name, contacts.business_name),
            updated_at=CURRENT_TIMESTAMP
            RETURNING id
        """, (phone_number, business_name, contact_name, email, interest_level)) as cursor:
            row = await cursor.fetchone()
            await self.conn.commit()
            return row['id']

    async def log_call(self, contact_id, room_id, prompt_id=None, duration_seconds=None, interest_level=None, objection=None, notes=None, email_captured=False, call_status="completed", transcript=None, captured_data=None):
        json_data = json.dumps(captured_data) if captured_data else '{}'
        async with self.conn.execute("""
            INSERT INTO calls (contact_id, room_id, prompt_id, duration_seconds, interest_level, objection, notes, email_captured, call_status, transcript, captured_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (contact_id, room_id, prompt_id, duration_seconds, interest_level, objection, notes, email_captured, call_status, transcript, json_data)) as cursor:
            row = await cursor.fetchone()
            await self.conn.commit()
            return row['id']

    async def update_call_recording(self, room_id: str, recording_url: str):
         await self.conn.execute("UPDATE calls SET recording_url = ? WHERE room_id = ?", (recording_url, room_id))
         await self.conn.commit()

    async def get_agent_config(self, slug: str = "default-agent") -> Optional[Dict[str, Any]]:
        return None

    async def get_ai_config(self, name: str = "default_telephony_config") -> Optional[Dict[str, Any]]:
        return None

    async def get_data_schema(self, slug: str = "default_roofing_agent") -> List[Dict[str, Any]]:
        return []

    async def get_webhooks(self, slug: str) -> List[Dict[str, Any]]:
        return []

    async def update_contact_email(self, contact_id: Union[int, str], email: str):
        pass

    async def get_prompt_id(self, name: str = "default_roofing_agent") -> Optional[int]:
        return 1

    async def track_objection(self, objection_text: str, response_text: Optional[str] = None):
        pass


async def get_db() -> Union[NeonDB, SQLiteDB]:
    """Create a new database instance for each job."""
    if os.getenv("NEON_DATABASE_URL"):
        db = NeonDB()
    else:
        logger.warning("Using SQLite fallback database")
        db = SQLiteDB()
    await db.connect()
    return db
