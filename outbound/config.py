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

async def prepare_instructions(db: Any, agent_slug: str, schema_fields: Any) -> str:
    """
    Fetches the active prompt and injects schema instructions.
    """
    # Fetch instructions
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

    return agent_instructions

async def load_ai_config(db: Any) -> Dict[str, Any]:
    """
    Loads AI configuration (LLM/STT/TTS settings).
    """
    ai_config = await db.get_ai_config("default_telephony_config")
    if not ai_config:
        ai_config = {
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
            "llm_temperature": 0.7,
            "stt_provider": "deepgram",
            "stt_model": "nova-3",
            "stt_language": "en-US",
            "tts_provider": "openai",
            "tts_model": "tts-1",
            "tts_voice": "alloy",
        }
    return ai_config
