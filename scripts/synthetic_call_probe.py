import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
from urllib import error, request


def _http_json(method: str, url: str, payload: Optional[Dict[str, Any]] = None, api_key: str = "") -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url=url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("x-api-key", api_key)
    with request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data) if data else None


def _latest_probe_call(
    calls: List[Dict[str, Any]],
    probe_business_name: str,
    min_id: int,
    phone_number: str,
) -> Optional[Dict[str, Any]]:
    for call in calls:
        if not isinstance(call.get("id"), int) or call["id"] <= min_id:
            continue
        if call.get("phone_number") != phone_number:
            continue
        if call.get("business_name") == probe_business_name:
            return call

        captured = call.get("captured_data") or {}
        if isinstance(captured, dict) and captured.get("business_name") == probe_business_name:
            return call
    return None


def _newest_call_after_id(calls: List[Dict[str, Any]], min_id: int, phone_number: str) -> Optional[Dict[str, Any]]:
    candidates = [
        call
        for call in calls
        if isinstance(call.get("id"), int)
        and call["id"] > min_id
        and call.get("phone_number") == phone_number
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item["id"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic outbound-call reliability probe")
    parser.add_argument("--base-url", default=os.getenv("PROBE_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--phone-number", default=os.getenv("PROBE_PHONE_NUMBER", ""))
    parser.add_argument("--agent-slug", default=os.getenv("PROBE_AGENT_SLUG", "roofing_agent"))
    parser.add_argument("--from-number", default=os.getenv("PROBE_FROM_NUMBER", ""))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("PROBE_TIMEOUT_SECONDS", "120")))
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--api-key", default=os.getenv("API_SECRET_KEY", ""))
    args = parser.parse_args()

    if not args.phone_number:
        print("ERROR: --phone-number (or PROBE_PHONE_NUMBER) is required")
        return 2

    probe_business_name = f"synthetic-probe-{int(time.time())}"
    outbound_payload: Dict[str, Any] = {
        "phone_number": args.phone_number,
        "business_name": probe_business_name,
        "agent_slug": args.agent_slug,
    }
    if args.from_number:
        outbound_payload["from_number"] = args.from_number

    try:
        existing_calls = _http_json("GET", f"{args.base_url}/dashboard/calls?limit=30", api_key=args.api_key)
    except Exception:
        existing_calls = []
    existing_ids = [c.get("id") for c in existing_calls if isinstance(c, dict) and isinstance(c.get("id"), int)]
    baseline_max_id = max(existing_ids) if existing_ids else 0

    try:
        print(f"[probe] triggering outbound call to {args.phone_number}")
        _http_json("POST", f"{args.base_url}/outbound-call", outbound_payload, api_key=args.api_key)
    except error.HTTPError as e:
        print(f"ERROR: outbound trigger failed with status {e.code}: {e.read().decode('utf-8', errors='replace')}")
        return 1
    except Exception as e:
        print(f"ERROR: outbound trigger failed: {e}")
        return 1

    deadline = time.time() + args.timeout
    last_state = None

    while time.time() < deadline:
        try:
            calls = _http_json("GET", f"{args.base_url}/dashboard/calls?limit=30", api_key=args.api_key)
        except Exception as e:
            print(f"[probe] warning: failed to fetch dashboard calls: {e}")
            time.sleep(args.poll_interval)
            continue

        call_list = calls if isinstance(calls, list) else []
        latest = _newest_call_after_id(call_list, baseline_max_id, args.phone_number)
        if latest is None:
            latest = _latest_probe_call(
                call_list,
                probe_business_name,
                min_id=baseline_max_id,
                phone_number=args.phone_number,
            )
        if latest:
            captured = latest.get("captured_data") or {}
            sm = captured.get("state_machine") or {}
            current_state = sm.get("current_state")
            if current_state and current_state != last_state:
                print(f"[probe] state={current_state}")
                last_state = current_state

            call_status = latest.get("call_status")
            if call_status in {"completed", "failed"}:
                print("[probe] finished")
                print(json.dumps(
                    {
                        "id": latest.get("id"),
                        "status": call_status,
                        "duration_seconds": latest.get("duration_seconds"),
                        "state_machine": sm,
                        "dial_attempts": captured.get("dial_attempts", []),
                    },
                    indent=2,
                ))
                return 0 if call_status == "completed" else 1

        time.sleep(args.poll_interval)

    print("ERROR: probe timed out before call reached terminal status")
    return 1


if __name__ == "__main__":
    sys.exit(main())
