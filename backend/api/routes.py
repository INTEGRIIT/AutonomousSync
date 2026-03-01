from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from shared.schemas.sensor_packet import SensorPacket
from backend.api.runtime import runtime
from backend.storage.jsonl_store import JSONLStore
from backend.utils.jsonx import loads, dumps
from backend.sensors.sanity import vec3_to_np
from backend.sync_engine.actions import snapshot_action
from backend.push.registry import register_device, all_devices, get_device
from backend.push.sender import send_push

import time
import os
import re
from typing import Optional

router = APIRouter()

# =========================================================
# LOGGING PATHS
# =========================================================

LOG_DIR = "logs"
UNIFIED_LOG_PATH = os.path.join(LOG_DIR, "sensor_stream.jsonl")
DEVICES_DIR = os.path.join(LOG_DIR, "devices")

# Keep a unified stream log (recommended for global auditing)
unified_store = JSONLStore(UNIFIED_LOG_PATH)

# Ensure device log folder exists
os.makedirs(DEVICES_DIR, exist_ok=True)


def safe_filename(s: str) -> str:
    """
    Enterprise safety: prevent path traversal / weird characters in filenames.
    Allows: a-zA-Z0-9._-
    """
    s = (s or "").strip()
    s = re.sub(r"[^a-zA-Z0-9._-]", "_", s)
    return s[:120] or "unknown"


def read_last_jsonl_lines(path: str, n: int) -> list[dict]:
    if not os.path.exists(path):
        return []
    n = max(1, min(5000, n))
    with open(path, "r", encoding="utf-8") as f:
        lines = [loads(x) for x in f.readlines()[-n:] if x.strip()]
    return lines


# =========================================================
# HTTP ROUTES
# =========================================================

@router.get("/health")
def health():
    return {"ok": True}


@router.get("/state/latest")
def latest():
    return runtime.latest or {"state": "—"}


@router.get("/state/timeline")
def timeline(n: int = 120):
    items = (runtime.timeline or [])[-max(1, min(1000, n)):]
    return {"items": items}


@router.get("/logs/recent")
def logs_recent(n: int = 50):
    """
    Unified log tail (all devices).
    """
    return {"items": read_last_jsonl_lines(UNIFIED_LOG_PATH, n)}


@router.get("/logs/device/{device_uid}")
def logs_device(device_uid: str, n: int = 200):
    """
    Per-device log tail.
    """
    uid = safe_filename(device_uid)
    device_path = os.path.join(DEVICES_DIR, f"{uid}.jsonl")
    return {"device_uid": device_uid, "items": read_last_jsonl_lines(device_path, n)}


# =========================================================
# PUSH REGISTRATION
# =========================================================

@router.post("/push/register")
async def push_register(payload: dict):
    device_uid = payload["device_uid"]
    device_name = payload["device_name"]
    token = payload["push_token"]
    platform = payload.get("platform")

    register_device(device_uid, device_name, token, platform)
    return {"ok": True, "device_uid": device_uid, "device_name": device_name}


# =========================================================
# PUSH TEST
# =========================================================

@router.post("/push/test")
def test_push(data: dict):
    device_uid = data.get("device_uid")
    if not device_uid:
        return {"ok": False, "error": "device_uid_required"}

    ok = send_push(
        device_uid=device_uid,
        title="🔔 Push Test",
        body="If you see this, backend push logic is firing.",
        data={"test": True},
        silent=False,
    )

    return {"ok": bool(ok), "device_uid": device_uid}


# =========================================================
# DEBUG
# =========================================================

@router.get("/push/devices")
def list_push_devices():
    return all_devices()


# =========================================================
# WEBSOCKET STREAM
# =========================================================

@router.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    await ws.accept()

    # Create per-socket device store lazily on first packet (once we know device_uid)
    device_store: Optional[JSONLStore] = None
    device_uid_for_log: Optional[str] = None

    try:
        while True:
            raw = await ws.receive_text()
            data = loads(raw)
            packet = SensorPacket(**data)
            # Lookup device metadata from registry
            record = get_device(packet.device_uid)
            device_name = record["device_name"] if record else None
            platform = record.get("platform") if record else None

            # Init per-device log store ONCE
            if device_store is None:
                device_uid_for_log = safe_filename(packet.device_uid)
                device_log_path = os.path.join(DEVICES_DIR, f"{device_uid_for_log}.jsonl")
                device_store = JSONLStore(device_log_path)

            acc = vec3_to_np(packet.accel) if packet.accel else None
            gyr = vec3_to_np(packet.gyro) if packet.gyro else None

            if acc is None or gyr is None:
                await ws.send_text(dumps({"error": "accel_and_gyro_required"}))
                continue

            feats = runtime.fusion.step(packet.ts, acc, gyr)
            touch_active = bool(packet.touch.active) if packet.touch else False
            moisture_val = packet.moisture.value if packet.moisture else None

            temporal = runtime.temporal.update(packet.ts, feats, touch_active, moisture_val)
            water = runtime.water.infer(temporal)

            state = runtime.sm.classify(feats, temporal, water, touch_active).value
            transition = runtime.state_transition.update(state)

            emergency_intent = None
            if temporal.get("free_fall"):
                emergency_intent = {"reason": "free_fall"}
            elif temporal.get("impact"):
                emergency_intent = {"reason": "impact"}
            elif temporal.get("water_emergency"):
                emergency_intent = {"reason": "water_detected"}

            decision = runtime.sync.decide(
                state=state,
                stable_duration_ms=int(temporal.get("stable_duration_ms", 0)),
                emergency=emergency_intent,
            )

            action = None
            push_ok = None

            if decision.get("sync"):
                action = snapshot_action({
                    "device_uid": packet.device_uid,
                    "state": state,
                    "type": decision.get("type"),
                    "reason": decision.get("reason"),
                    "priority": decision.get("priority"),
                })

                if decision.get("notify"):
                    push_ok = send_push(
                        device_uid=packet.device_uid,
                        title="⚠️ Emergency Backup" if decision.get("type") == "EMERGENCY" else "Autonomous Sync",
                        body=decision.get("reason", "Snapshot captured"),
                        data={"state": state},
                        silent=False,
                    )

            out = {
                "ts": time.time(),

                # Identity
                "device_uid": packet.device_uid,
                "device_name": device_name,
                "platform": platform,

                # State + transitions
                "state": state,
                "transition": transition,

                # Decision layer
                "decision": decision,
                "action": action,

                # Feature layers (ML gold)
                "features": feats,
                "temporal": temporal,
                "water": water,
                "emergency": emergency_intent,

                # Push tracking
                "push": {"sent": bool(push_ok)} if push_ok is not None else None,
            }

            runtime.latest = out
            runtime.timeline.append(out)
            runtime.timeline = runtime.timeline[-250:]

            # Write BOTH:
            # 1) unified log
            unified_store.append({"in": data, "out": out})
            # 2) per-device log
            device_store.append({"in": data, "out": out})

            await ws.send_text(dumps(out))

    except WebSocketDisconnect:
        return
    except Exception as e:
        # Don't crash silently; surface something useful
        try:
            await ws.send_text(dumps({"error": "server_exception", "detail": str(e)}))
        except Exception:
            pass
        return