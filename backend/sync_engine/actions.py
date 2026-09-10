from backend.utils.time import now_ms
from backend.backup.service import BackupService
import uuid

# Initialize once (singleton style)
backup_service = BackupService()


def snapshot_action(payload: dict) -> dict:
    """
    Create a snapshot action event.

    This represents an authoritative system action that may trigger:
    - cloud sync
    - notification
    - audit logging
    """

    try:
        print("🔥 SNAPSHOT_ACTION CALLED")

        device_uid = payload.get("device_uid") or payload.get("device_id")

        if not device_uid:
            print("[snapshot_action] ❌ missing device_uid")
            return {
                "ok": False,
                "error": "missing_device_uid",
            }

        snapshot_payload = {
            "device_uid": device_uid,
            "state": payload.get("state"),
            "reason": payload.get("reason"),
            "priority": payload.get("priority"),
            "type": payload.get("type"),

            # Optional extensions
            "telemetry": payload.get("telemetry", {}),
            "decision": payload,
        }

        print("📦 SNAPSHOT PAYLOAD:", snapshot_payload)

        # --------------------------------------------------
        # 🔥 ACTUAL SNAPSHOT CREATION
        # --------------------------------------------------

        result = backup_service.store_snapshot(snapshot_payload)

        print("📦 SNAPSHOT STORE RESULT:", result)

        if not result or not result.get("ok"):
            print("[snapshot_action] ❌ snapshot failed:", result)
            return {
                "ok": False,
                "error": result.get("error") if result else "unknown_error",
            }

        snapshot_id = result.get("snapshot_id")

        if not snapshot_id:
            print("[snapshot_action] ❌ missing snapshot_id")
            return {
                "ok": False,
                "error": "missing_snapshot_id",
            }

        # --------------------------------------------------
        # ✅ FINAL RETURN OBJECT (CRITICAL)
        # --------------------------------------------------

        action = {
            "ok": True,  # 🔥 REQUIRED FOR PUSH SYSTEM
            "snapshot_id": snapshot_id,

            "id": str(uuid.uuid4()),
            "type": "SYNC_ACTION",
            "action": "SNAPSHOT_CREATED",
            "severity": payload.get("type", "GRACEFUL"),
            "priority": payload.get("priority", "LOW"),
            "reason": payload.get("reason"),
            "ts": now_ms(),

            # 🔥 FIX: NO MORE DEDUPE COLLISIONS
            "dedupe_key": f"{device_uid}:{uuid.uuid4()}",

            "summary": {
                "device_uid": device_uid,
                "state": payload.get("state"),
                "classification": payload.get("type", "GRACEFUL"),
            },
        }

        print("✅ SNAPSHOT ACTION FINAL:", action)

        return action

    except Exception as e:
        print(f"[snapshot_action] ❌ exception: {e}")
        return {
            "ok": False,
            "error": str(e),
        }
