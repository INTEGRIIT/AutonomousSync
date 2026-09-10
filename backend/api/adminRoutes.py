# backend/api/adminRoutes.py
#
# Research-device flagging.
#
# WHY THIS EXISTS
# Once the app is on TestFlight, ordinary testers stream telemetry into
# the same logs and collections as the labelled research runs. Two
# problems follow: the paper's dataset silently mixes trial data with
# strangers' real-world phone motion, and those testers never consented
# to being in a research dataset.
#
# Flagging devices at the source solves both. A flagged device shows
# Trial Mode in the UI and stamps `research: true` on every packet, so
# analysis can separate the two populations cleanly instead of guessing
# after the fact.
#
# The unlock code lives in .env as RESEARCH_UNLOCK_CODE. This is a
# convenience gate for a small research team, not an authentication
# system — it keeps testers out of research mode, nothing more.

import hmac
import os

from fastapi import APIRouter

from backend.db import events_collection

router = APIRouter()

_db = events_collection.database
devices = _db["devices"]

UNLOCK_CODE = os.getenv("RESEARCH_UNLOCK_CODE", "")


def _ok(code: str) -> bool:
    """Constant-time compare; refuse outright if no code is configured."""
    if not UNLOCK_CODE:
        return False
    return hmac.compare_digest(str(code or ""), UNLOCK_CODE)


@router.post("/admin/research-device")
async def set_research_device(payload: dict):
    if not _ok(payload.get("code")):
        return {"ok": False, "error": "invalid code"}

    device_uid = payload.get("device_uid")
    if not device_uid:
        return {"ok": False, "error": "device_uid required"}

    enabled = bool(payload.get("enabled", True))
    member = payload.get("member")

    update = {"is_research_device": enabled}
    if member:
        update["research_member"] = member

    res = devices.update_one({"device_uid": device_uid}, {"$set": update},
                             upsert=True)
    return {
        "ok": True,
        "device_uid": device_uid,
        "is_research_device": enabled,
        "matched": res.matched_count,
    }


@router.get("/admin/research-device")
async def get_research_device(device_uid: str):
    """
    Unauthenticated on purpose: it reveals only whether one device the
    caller already knows the UID of is flagged. The app calls this at
    startup to restore its own state.
    """
    rec = devices.find_one({"device_uid": device_uid},
                           {"_id": 0, "is_research_device": 1,
                            "research_member": 1})
    return {
        "ok": True,
        "is_research_device": bool((rec or {}).get("is_research_device")),
        "member": (rec or {}).get("research_member"),
    }


@router.get("/admin/research-devices")
async def list_research_devices(code: str):
    if not _ok(code):
        return {"ok": False, "error": "invalid code"}
    rows = list(devices.find(
        {"is_research_device": True},
        {"_id": 0, "device_uid": 1, "device_name": 1, "platform": 1,
         "research_member": 1, "last_seen": 1},
    ))
    for r in rows:
        if r.get("last_seen"):
            r["last_seen"] = r["last_seen"].isoformat(timespec="seconds")
    return {"ok": True, "count": len(rows), "devices": rows}
