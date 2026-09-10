import csv
import io
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, StreamingResponse
from shared.schemas.sensor_packet import SensorPacket
from backend.api.runtime import runtime
from backend.storage.jsonl_store import JSONLStore
from backend.utils.jsonx import loads, dumps
from backend.sensors.sanity import vec3_to_np
from backend.sync_engine.actions import snapshot_action
from backend.push.sender import send_push
from backend.db import (
    upsert_device,
    get_device,
    get_all_devices,
    insert_event,
    insert_snapshot,
    events_collection,
)

import time
import os
import re
import uuid
import csv
import io
from datetime import datetime
from typing import Optional
from backend.storage.s3_service import upload_file_to_s3

router = APIRouter()

# =========================================================
# LOGGING PATHS
# =========================================================

LOG_DIR = "logs"
UNIFIED_LOG_PATH = os.path.join(LOG_DIR, "sensor_stream.jsonl")
DEVICES_DIR = os.path.join(LOG_DIR, "devices")

unified_store = JSONLStore(UNIFIED_LOG_PATH)
os.makedirs(DEVICES_DIR, exist_ok=True)


def safe_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^a-zA-Z0-9._-]", "_", s)
    return s[:120] or "unknown"


def read_last_jsonl_lines(path: str, n: int) -> list[dict]:
    if not os.path.exists(path):
        return []
    n = max(1, min(5000, n))
    with open(path, "r", encoding="utf-8") as f:
        return [loads(x) for x in f.readlines()[-n:] if x.strip()]


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
    return {"items": (runtime.timeline or [])[-max(1, min(1000, n)): ]}


@router.get("/logs/recent")
def logs_recent(n: int = 50):
    return {"items": read_last_jsonl_lines(UNIFIED_LOG_PATH, n)}


@router.get("/logs/device/{device_uid}")
def logs_device(device_uid: str, n: int = 200):
    uid = safe_filename(device_uid)
    path = os.path.join(DEVICES_DIR, f"{uid}.jsonl")
    return {"device_uid": device_uid, "items": read_last_jsonl_lines(path, n)}


@router.get("/device/{device_uid}")
def get_device_info(device_uid: str):
    device = get_device(device_uid)

    if not device:
        return {"ok": False}

    return {
        "ok": True,
        "device_uid": device_uid,
        "device_name": device.get("device_name"),
        "preferences": device.get("preferences"),
    }

# =========================================================
# PUSH REGISTRATION (NOW STORES PREFERENCES)
# =========================================================

@router.post("/push/register")
async def push_register(payload: dict):
    try:
        device_uid = payload.get("device_uid")
        push_token = payload.get("push_token")

        if not device_uid or not push_token:
            return {"ok": False, "error": "missing_fields"}

        upsert_device(
            device_uid=device_uid,
            device_name=payload.get("device_name"),
            push_token=push_token,
            platform=payload.get("platform"),
            preferences=payload.get("preferences"),  # 🔥 persistence
        )

        return {"ok": True}

    except Exception as e:
        print("[push] register error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# PUSH TEST
# =========================================================

@router.post("/push/test")
def test_push(data: dict):
    device_uid = data.get("device_uid")

    if not device_uid:
        return {"ok": False, "error": "device_uid_required"}

    device = get_device(device_uid)
    if not device:
        return {"ok": False, "error": "device_not_found"}

    ok = send_push(
        device_uid=device_uid,
        title="Push Test",
        body="Push system working.",
        data={"test": True},
        silent=False,
    )

    return {"ok": bool(ok)}


@router.get("/push/devices")
def list_push_devices():
    return get_all_devices()



@router.post("/upload")
async def upload_file(
    device_uid: str = Form(...),
    device_name: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()

        print("🔥 USER ID RECEIVED:", user_id)
        print("🔥 DEVICE NAME RECEIVED:", device_name)

        # 🚫 Block bad data
        if not user_id or user_id == "anonymous":
            return {"ok": False, "error": "user_id_required"}

        result = upload_file_to_s3(
            file_bytes=contents,
            filename=file.filename,
            device_uid=device_uid,
            user_id=user_id,           # ✅ FIX
            device_name=device_name    # ✅ FIX
        )

        if not result["ok"]:
            return {"ok": False, "error": result["error"]}

        # ✅ Save metadata (with user context)
        insert_snapshot({
            "snapshot_id": str(uuid.uuid4()),
            "device_uid": device_uid,
            "device_name": device_name,
            "user_id": user_id,
            "filename": file.filename,
            "s3_key": result["key"],
            "url": result["url"],
            "ts": time.time(),
        })

        print(f"📂 FILE UPLOADED → {result['key']}")

        return {
            "ok": True,
            "url": result["url"]
        }

    except Exception as e:
        print("❌ Upload route error:", e)
        return {"ok": False, "error": str(e)}
    

@router.get("/events/export/{device_uid}")
def export_events(device_uid: str):
    try:
        events = list(
            events_collection.find(
                {"device_uid": device_uid},
                {"_id": 0}
            ).sort("timestamp", -1)
        )

        if not events:
            return {"ok": False, "error": "no_events"}

        normalized = []
        for event in events:
            row = {}
            for key, value in event.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif isinstance(value, dict):
                    row[key] = str(value)
                else:
                    row[key] = value
            normalized.append(row)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=normalized[0].keys())
        writer.writeheader()
        writer.writerows(normalized)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=events_{device_uid}.csv"
            },
        )

    except Exception as e:
        print("❌ export error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# WEBSOCKET STREAM (ELITE VERSION)
# =========================================================

@router.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    await ws.accept()

    device_store: Optional[JSONLStore] = None

    try:
        while True:
            try:
                raw = await ws.receive_text()
                data = loads(raw)
                packet = SensorPacket(**data)
            except Exception:
                await ws.send_text(dumps({"error": "invalid_packet"}))
                continue

            now = time.time()

            # =============================
            # DEVICE LOOKUP (SINGLE CALL)
            # =============================

            record = get_device(packet.device_uid)
            device_name = record.get("device_name") if record else None
            platform = record.get("platform") if record else None

            # heartbeat update (NO overwrite of prefs)
            if record:
                upsert_device(
                    device_uid=packet.device_uid,
                    device_name=device_name,
                    push_token=record.get("push_token"),
                    platform=platform,
                    preferences=record.get("preferences"),
                )

            # =============================
            # DEVICE LOG INIT
            # =============================

            if device_store is None:
                uid = safe_filename(packet.device_uid)
                device_store = JSONLStore(os.path.join(DEVICES_DIR, f"{uid}.jsonl"))

            acc = vec3_to_np(packet.accel) if packet.accel else None
            gyr = vec3_to_np(packet.gyro) if packet.gyro else None

            if acc is None or gyr is None:
                await ws.send_text(dumps({"error": "accel_and_gyro_required"}))
                continue

            # =============================
            # PIPELINE
            # =============================

            feats = runtime.fusion.step(packet.ts, acc, gyr)

            temporal = runtime.temporal.update(
                packet.ts,
                feats,
                bool(packet.touch.active) if packet.touch else False,
                packet.moisture.value if packet.moisture else None,
            )

            water = runtime.water.infer(temporal)

            state = runtime.sm.classify(
                feats,
                temporal,
                water,
                bool(packet.touch.active) if packet.touch else False,
            ).value

            transition = runtime.state_transition.update(state)

            # =============================
            # 🔥 USER PREFERENCES (FINAL)
            # =============================

            prefs = record.get("preferences", {}) if record else {}

            packet_prefs = getattr(packet, "preferences", None)
            if isinstance(packet_prefs, dict):
                prefs = {**prefs, **packet_prefs}

            if not isinstance(prefs, dict):
                prefs = {}

            # 🔥 normalize defaults
            prefs = {
                "auto_backup": True,
                "alert_sensitivity": "high",
                "include_battery": True,
                "include_telemetry": True,
                **prefs,
            }

            auto_backup_enabled = prefs["auto_backup"]
            alert_sensitivity = prefs["alert_sensitivity"]
            include_battery = prefs["include_battery"]
            include_telemetry = prefs["include_telemetry"]

            print("⚙️ PREFS:", prefs)

            # =============================
            # EMERGENCY DETECTION
            # =============================

            emergency_intent = None

            if temporal.get("free_fall"):
                emergency_intent = {"reason": "free_fall"}
            elif temporal.get("impact"):
                emergency_intent = {"reason": "impact"}
            elif temporal.get("water_emergency"):
                emergency_intent = {"reason": "water_detected"}

            # sensitivity filter
            if alert_sensitivity == "low":
                if emergency_intent and emergency_intent["reason"] in {"free_fall", "impact"}:
                    emergency_intent = None
            elif alert_sensitivity == "medium":
                if emergency_intent and emergency_intent["reason"] == "free_fall":
                    emergency_intent = None

            decision = runtime.sync.decide(
                state=state,
                stable_duration_ms=int(temporal.get("stable_duration_ms", 0)),
                emergency=emergency_intent,
            )

            # disable override
            if not auto_backup_enabled:
                print("⛔ AUTO BACKUP DISABLED")
                decision = {
                    "sync": False,
                    "reason": "disabled_by_user",
                    "type": "DISABLED",
                }

            action = None
            push_ok = None

            # =============================
            # SNAPSHOT + PUSH
            # =============================

            print("🚀 DECISION:", decision)

            if decision.get("sync"):
                action = snapshot_action({
                    "device_uid": packet.device_uid,
                    "state": state,
                    "type": decision.get("type"),
                    "reason": decision.get("reason"),
                    "priority": decision.get("priority"),
                    "features": feats,
                    "temporal": temporal,
                    "water": water,
                    "telemetry": {
                        "battery": packet.battery.dict() if (packet.battery and include_battery) else None,
                        "touch": packet.touch.dict() if (packet.touch and include_telemetry) else None,
                        "preferences": prefs,
                    },
                    "decision": decision,
                })

                if action and action.get("ok"):
                    try:
                        push_ok = send_push(
                            device_uid=packet.device_uid,
                            title="Emergency Backup",
                            body="Uploading selected files...",
                            data={
                                "action": "UPLOAD",  # 🔥 THIS IS THE KEY
                                "snapshot_id": action.get("snapshot_id"),
                                "state": state,
                            },
                            silent=False,
                        )
                    except Exception as e:
                        print("❌ PUSH ERROR:", e)
                        push_ok = False
                else:
                    push_ok = False

                # DB
                insert_event({
                    "event_id": str(uuid.uuid4()),
                    "device_uid": packet.device_uid,
                    "device_name": device_name,
                    "platform": platform,

                    "event_type": decision.get("type"),
                    "reason": decision.get("reason"),
                    "state": state,

                    "sync_triggered": decision.get("sync"),
                    "snapshot_id": action.get("snapshot_id") if action else None,

                    "push_attempted": decision.get("sync") is True,
                    "push_success": bool(push_ok),

                    "features": {
                        "acc_norm": feats.get("acc_norm"),
                        "jerk": feats.get("jerk"),
                    },

                    "temporal": {
                        "free_fall": temporal.get("free_fall"),
                        "impact": temporal.get("impact"),
                        "water_emergency": temporal.get("water_emergency"),
                        "stable_duration_ms": temporal.get("stable_duration_ms"),
                    },

                    "timestamp": datetime.utcnow(),
                })

                if action and action.get("ok"):
                    insert_snapshot({
                        "snapshot_id": action.get("snapshot_id"),
                        "device_uid": packet.device_uid,
                        "type": decision.get("type"),
                        "status": "stored",
                        "ts": time.time(),
                    })

            # =============================
            # OUTPUT
            # =============================

            out = {
                "ts": now,
                "device_uid": packet.device_uid,
                "device_name": device_name,
                "platform": platform,
                "state": state,
                "transition": transition,
                "decision": decision,
                "snapshot": {
                    "created": bool(action and action.get("ok")),
                    "id": action.get("snapshot_id") if action else None,
                },
                "features": feats,
                "temporal": temporal,
                "water": water,
                "emergency": emergency_intent,
                "push": {"sent": bool(push_ok)} if push_ok is not None else None,
                "preferences": prefs,
            }

            runtime.latest = out
            runtime.timeline.append(out)
            runtime.timeline = runtime.timeline[-250:]

            unified_store.append({"in": data, "out": out})
            device_store.append({"in": data, "out": out})

            await ws.send_text(dumps(out))

    except WebSocketDisconnect:
        print("[ws] disconnected")
    except Exception as e:
        print("[ws] fatal error:", e)


