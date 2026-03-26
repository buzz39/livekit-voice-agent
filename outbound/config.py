import logging
from typing import Dict, Any, Tuple
from webhook_dispatcher import WebhookDispatcher

logger = logging.getLogger("outbound.config")

async def load_agent_config(db: Any, agent_slug: str) -> Tuple[Dict[str, Any], Any, WebhookDispatcher, str]:
    """
    Fetches agent configuration, schema, and webhooks from the database.
    Returns (agent_config, schema_fields, dispatcher, final_agent_slug).
    """
    # Fetch agent configuration
    agent_config = await db.get_agent_config(agent_slug)
    if not agent_config:
        logger.warning(f"Agent {agent_slug} not found, falling back to default")
        agent_slug = "default_roofing_agent"
        agent_config = await db.get_agent_config(agent_slug) or {}

    # Fetch schema & webhooks
    schema_fields = await db.get_data_schema(agent_slug)
    webhooks = await db.get_webhooks(agent_slug)
    dispatcher = WebhookDispatcher(webhooks, agent_slug)

    return agent_config, schema_fields, dispatcher, agent_slug

async def prepare_instructions(db: Any, agent_slug: str, schema_fields: Any, agent_config: dict = None) -> str:
    """
    Fetches the active prompt and injects schema instructions.
    Uses prompt_id from agent_config if available, otherwise falls back to slug name.
    """
    agent_instructions = None

    # Prefer prompt_id from agent_config (DB-driven link)
    if agent_config and agent_config.get("prompt_id"):
        agent_instructions = await db.get_prompt_content_by_id(agent_config["prompt_id"])

    # Fallback: look up prompt by agent slug name
    if not agent_instructions:
        agent_instructions = await db.get_active_prompt(agent_slug)

    if not agent_instructions:
        agent_instructions = "You are a professional caller."

    # Inject schema into instructions
    if schema_fields:
        schema_prompt = "\n\nYou are authorized to collect the following information:\n"
        for field in schema_fields:
            schema_prompt += f"- {field['field_name']}: {field.get('description', '')}\n"
        schema_prompt += "\nUse the `update_call_data` tool to save these values."
        agent_instructions += schema_prompt

    # --- Objection Handling Injection ---
    try:
        objections = await db.get_all_objections(agent_slug=agent_slug)
        if objections:
            agent_instructions += "\n\n## Objection Handling\n"
            agent_instructions += "When the caller raises these objections, respond as specified:\n"
            for obj in objections:
                trigger = obj.get("objection_text", "")
                response = obj.get("response_text", "")
                if trigger and response:
                    agent_instructions += f'- If they say "{trigger}": {response}\n'
    except Exception as e:
        logger.warning(f"Failed to load objections for {agent_slug}: {e}")

    # Add required behavioral instructions
    additional_instructions = """

    IMPORTANT BEHAVIORAL INSTRUCTIONS:
    1. If you collect an email address, spell it back to the user character by character and ask them to confirm before saving with `update_call_data`.
    2. CALL TERMINATION: When the conversation is complete, say goodbye and then call the `end_call` tool.
    3. If you detect a voicemail greeting or a "mailbox is full" message, call the `end_call` tool.
    """
    agent_instructions += additional_instructions

    return agent_instructions

async def load_ai_config(db: Any, agent_slug: str = None, agent_config: dict = None) -> Dict[str, Any]:
    """
    Loads AI configuration (LLM/STT/TTS settings).
    Prioritizes ai_config_name from agent_config, then slug, then default.
    """
    ai_config = None

    # Prefer ai_config_name from agent_config (DB-driven link)
    if agent_config and agent_config.get("ai_config_name"):
        ai_config = await db.get_ai_config(agent_config["ai_config_name"])

    if not ai_config and agent_slug:
        # Try to find config named after the agent slug
        ai_config = await db.get_ai_config(agent_slug)

    if not ai_config:
        ai_config = await db.get_ai_config("default_telephony_config")

    if not ai_config:
        ai_config = {
            "llm_provider": "groq",
            "llm_model": "llama-3.3-70b-versatile",
            "llm_temperature": 0.7,
            "stt_provider": "deepgram",
            "stt_model": "nova-3",
            "stt_language": "en-US",
            "tts_provider": "cartesia",
            "tts_model": "sonic-2",
            "tts_voice": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
        }
    return ai_config
