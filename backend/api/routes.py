from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from shared.schemas.sensor_packet import SensorPacket
from backend.api.runtime import runtime
from backend.storage.jsonl_store import JSONLStore
from backend.utils.jsonx import loads, dumps
from backend.sensors.sanity import vec3_to_np
from backend.sync_engine.actions import snapshot_action
from backend.push.registry import register_device, all_devices
from backend.push.sender import send_push

import time
import os

router = APIRouter()

LOG_PATH = os.path.join("logs", "sensor_stream.jsonl")
store = JSONLStore(LOG_PATH)

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
    if not os.path.exists(LOG_PATH):
        return {"items": []}

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = [loads(x) for x in f.readlines()[-n:] if x.strip()]

    return {"items": lines}


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


# =========================================================
# PUSH TEST (SYNC — FIXED)
# =========================================================

@router.post("/push/test")
def test_push(data: dict):
    device_uid = data.get("device_uid")

    ok = send_push(
        device_uid=device_uid,
        title="🔔 Push Test",
        body="If you see this, backend push logic is firing.",
        data={"test": True},
    )

    return {
        "ok": ok,
        "device_uid": device_uid,
    }


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

    try:
        while True:
            raw = await ws.receive_text()
            data = loads(raw)
            packet = SensorPacket(**data)

            acc = vec3_to_np(packet.accel) if packet.accel else None
            gyr = vec3_to_np(packet.gyro) if packet.gyro else None

            if acc is None or gyr is None:
                await ws.send_text(dumps({"error": "accel_and_gyro_required"}))
                continue

            feats = runtime.fusion.step(packet.ts, acc, gyr)
            touch_active = bool(packet.touch.active) if packet.touch else False
            moisture_val = packet.moisture.value if packet.moisture else None

            temporal = runtime.temporal.update(
                packet.ts, feats, touch_active, moisture_val
            )

            water = runtime.water.infer(temporal)

            state = runtime.sm.classify(
                feats, temporal, water, touch_active
            ).value

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
            if decision.get("sync"):
                action = snapshot_action({
                    "device_uid": packet.device_uid,
                    "state": state,
                    "type": decision.get("type"),
                    "reason": decision.get("reason"),
                    "priority": decision.get("priority"),
                })

                if decision.get("notify"):
                    send_push(
                        device_uid=packet.device_uid,
                        title="⚠️ Emergency Backup"
                        if decision.get("type") == "EMERGENCY"
                        else "Autonomous Sync",
                        body=decision.get("reason", "Snapshot captured"),
                        data={"state": state},
                    )

            out = {
                "ts": time.time(),
                "device_uid": packet.device_uid,
                "state": state,
                "transition": transition,
                "decision": decision,
                "action": action,
                "features": feats,
                "temporal": temporal,
                "water": water,
                "emergency": emergency_intent,
            }

            runtime.latest = out
            runtime.timeline.append(out)
            runtime.timeline = runtime.timeline[-250:]

            store.append({"in": data, "out": out})
            await ws.send_text(dumps(out))

    except WebSocketDisconnect:
        return