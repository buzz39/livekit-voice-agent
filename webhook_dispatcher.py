"""
Webhook Dispatcher for LiveKit Voice Agents

Handles sending webhook events to configured endpoints (e.g., n8n, Zapier, custom servers).
Supports multiple event types and retry logic.
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
import httpx

logger = logging.getLogger("webhook-dispatcher")


class WebhookDispatcher:
    """Dispatches webhook events to configured endpoints."""
    
    def __init__(self, webhooks: List[Dict[str, Any]], agent_slug: str):
        """
        Initialize webhook dispatcher.
        
        Args:
            webhooks: List of webhook configurations from database
            agent_slug: Agent identifier for logging
        """
        self.webhooks = webhooks or []
        self.agent_slug = agent_slug
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def dispatch(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Dispatch event to all matching webhooks.
        
        Args:
            event_type: Type of event (e.g., "call.started", "call.ended", "data.captured")
            payload: Event data to send
        """
        matching_webhooks = [
            wh for wh in self.webhooks 
            if wh.get("event_type") == event_type and wh.get("target_url")
        ]
        
        if not matching_webhooks:
            logger.debug(f"No webhooks configured for event: {event_type}")
            return
        
        # Add common metadata
        full_payload = {
            "event": event_type,
            "agent_slug": self.agent_slug,
            "timestamp": None,  # Will be set by receiver
            "data": payload
        }
        
        # Dispatch to all matching webhooks concurrently
        tasks = [
            self._send_webhook(wh, full_payload)
            for wh in matching_webhooks
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_webhook(self, webhook: Dict[str, Any], payload: Dict[str, Any]) -> None:
        """
        Send webhook to a single endpoint with retry logic.
        
        Args:
            webhook: Webhook configuration
            payload: Data to send
        """
        url = webhook["target_url"]
        headers = webhook.get("headers", {})
        
        # Parse headers if stored as JSON string
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                headers = {}
        
        # Add default headers
        headers.setdefault("Content-Type", "application/json")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                logger.info(f"Webhook dispatched successfully: {webhook.get('event_type')} -> {url}")
                return
                
            except httpx.HTTPError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Webhook failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Webhook failed after {max_retries} attempts: {e}")
            except Exception as e:
                logger.error(f"Unexpected error dispatching webhook: {e}")
                return
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
