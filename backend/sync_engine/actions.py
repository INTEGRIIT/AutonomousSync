from backend.utils.time import now_ms
import uuid


def snapshot_action(payload: dict) -> dict:
    """
    Create a snapshot action event.

    This represents an authoritative system action that may trigger:
    - cloud sync
    - notification
    - audit logging

    Payload is expected to include:
      - device_id
      - state
      - type: GRACEFUL | EMERGENCY
      - reason
      - priority
    """

    action_type = payload.get("type", "GRACEFUL")
    priority = payload.get("priority", "LOW")

    return {
        "id": str(uuid.uuid4()),              # unique action id
        "type": "SYNC_ACTION",
        "action": "SNAPSHOT_CREATED",
        "severity": action_type,              # GRACEFUL | EMERGENCY
        "priority": priority,                 # LOW | HIGH
        "reason": payload.get("reason"),
        "ts": now_ms(),

        # dedupe key (useful later for cloud + notifications)
        "dedupe_key": f"{payload.get('device_id')}:{action_type}",

        "summary": {
            "device_id": payload.get("device_id"),
            "state": payload.get("state"),
            "classification": action_type,
        },
    }