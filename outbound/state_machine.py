from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CallState(str, Enum):
    ROOM_CONNECTED = "room_connected"
    CONFIG_LOADED = "config_loaded"
    CALL_LOGGED = "call_logged"
    SESSION_STARTING = "session_starting"
    SESSION_READY = "session_ready"
    DIALING = "dialing"
    DIALED = "dialed"
    DIAL_FAILED = "dial_failed"
    RECORDING_STARTED = "recording_started"
    OPENING_PLAYING = "opening_playing"
    OPENING_PLAYED = "opening_played"
    OPENING_FAILED = "opening_failed"
    IN_CONVERSATION = "in_conversation"
    LLM_TIMEOUT_FALLBACK = "llm_timeout_fallback"
    PARTICIPANT_DISCONNECTED = "participant_disconnected"
    FINALIZING = "finalizing"
    FINALIZED = "finalized"
    FAILED = "failed"


@dataclass
class StateTransition:
    state: CallState
    at: str
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class CallStateMachine:
    def __init__(self) -> None:
        self.current: Optional[CallState] = None
        self.transitions: List[StateTransition] = []

    def transition(
        self,
        state: CallState,
        *,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        self.current = state
        self.transitions.append(
            StateTransition(
                state=state,
                at=now,
                reason=reason,
                details=details,
            )
        )

    def export(self) -> Dict[str, Any]:
        return {
            "current_state": self.current.value if self.current else None,
            "transitions": [
                {
                    "state": item.state.value,
                    "at": item.at,
                    "reason": item.reason,
                    "details": item.details,
                }
                for item in self.transitions
            ],
        }
