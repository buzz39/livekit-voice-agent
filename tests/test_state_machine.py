from outbound.state_machine import CallState, CallStateMachine


def test_state_machine_tracks_current_state_and_history() -> None:
    sm = CallStateMachine()
    sm.transition(CallState.ROOM_CONNECTED)
    sm.transition(CallState.DIALING, details={"phone_number": "+919876543210"})
    sm.transition(CallState.DIALED, reason="sip_answered")

    exported = sm.export()

    assert exported["current_state"] == "dialed"
    assert len(exported["transitions"]) == 3
    assert exported["transitions"][1]["details"]["phone_number"] == "+919876543210"
    assert exported["transitions"][2]["reason"] == "sip_answered"


def test_state_machine_uses_iso_timestamps() -> None:
    sm = CallStateMachine()
    sm.transition(CallState.SESSION_STARTING)
    at = sm.export()["transitions"][0]["at"]

    assert "T" in at
    assert at.endswith("Z")
