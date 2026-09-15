# backend/api/sessionRoutes.py
#
# Endpoints for the app's Session Mode and for exporting recorded
# sessions into the collection workbook.
#
# Also records network transitions. The client polls network state
# every ten seconds; when the type changes it posts here. That
# captures the WiFi-to-cellular handoff cases automatically rather
# than depending on an operator noticing they walked out of range.

import csv
import io

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.db_sessions import (
    EXPORT_COLUMNS,
    sessions,
    start_session,
    end_session,
    list_sessions,
    delete_session,
    next_session_number,
)

router = APIRouter()

VALID_TYPES = {
    "idle", "streaming_idle", "streaming_events",
    "walking_hand", "walking_pocket", "walking_bag",
    "running", "stairs", "cycling",
    "driving_mounted", "driving_loose",
    "desk", "stationary",
    "drop_trial_session", "other",
}


@router.post("/sessions/start")
async def sessions_start(payload: dict):
    if not payload.get("session_id") or not payload.get("device_uid"):
        return {"ok": False, "error": "session_id and device_uid required"}

    st = payload.get("session_type")
    if st and st not in VALID_TYPES:
        # Accept it anyway rather than block a recording mid-collection,
        # but flag it so an unexpected value is visible in analysis.
        payload["session_type_unrecognised"] = True

    # Resolve the member from the device record for the same reason
    # trials do: the label is a property of the device, not a per
    # session choice.
    try:
        from backend.api.adminRoutes import devices as _devices
        rec = _devices.find_one({"device_uid": payload["device_uid"]},
                                {"_id": 0, "research_member": 1})
        assigned = (rec or {}).get("research_member")
        if assigned:
            claimed = payload.get("member")
            if claimed and claimed != assigned:
                payload["member_claimed"] = claimed
            payload["member"] = assigned
    except Exception as e:
        print("session member resolution failed:", e)

    try:
        doc = start_session(payload)
        return {"ok": True, "session_id": doc["session_id"],
                "member": doc.get("member")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/sessions/end")
async def sessions_end(payload: dict):
    sid = payload.get("session_id")
    uid = payload.get("device_uid")
    if not sid or not uid:
        return {"ok": False, "error": "session_id and device_uid required"}
    try:
        rec = end_session(sid, uid,
                          packets=payload.get("packets"),
                          battery_end=payload.get("battery_end"),
                          network_changes=payload.get("network_changes"),
                          notes=payload.get("notes"))
        if not rec:
            return {"ok": False, "error": "session not found"}
        return {"ok": True, "session": rec}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/sessions")
async def sessions_list(device_uid: str = None, member: str = None,
                        session_type: str = None, limit: int = 1000):
    return {"ok": True,
            "sessions": list_sessions(device_uid, member, session_type, limit)}


@router.get("/sessions/next")
async def sessions_next(member: str):
    n = next_session_number(member)
    return {"ok": True, "next": n, "suggested_id": f"{member}-S{n:03d}"}


@router.delete("/sessions")
async def sessions_delete(session_id: str, device_uid: str):
    n = delete_session(session_id, device_uid)
    return {"ok": n > 0, "deleted": n}


@router.get("/sessions/export.csv")
async def sessions_export(member: str = None, session_type: str = None):
    rows = list_sessions(member=member, session_type=session_type,
                         limit=100000)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        out = dict(r)
        for k in ("started_at", "ended_at"):
            if out.get(k):
                out[k] = out[k].isoformat(timespec="seconds")
        w.writerow(out)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="sessions_{member or "all"}.csv"'},
    )


# =========================================================
# NETWORK TRANSITIONS
# =========================================================

@router.post("/network/transition")
async def network_transition(payload: dict):
    """
    Record a change in network type during a session.

    A transition is not a disconnection: the socket may survive a
    handoff from WiFi to cellular without ever reporting a loss, so
    fault-injection cases that induce an outage do not cover it. This
    is the common real-world case and it is worth having recorded
    automatically rather than relying on an operator noticing.
    """
    uid = payload.get("device_uid")
    if not uid:
        return {"ok": False, "error": "device_uid required"}
    doc = {
        "device_uid": uid,
        "session_id": payload.get("session_id"),
        "trial_id": payload.get("trial_id"),
        "from_type": payload.get("from_type"),
        "to_type": payload.get("to_type"),
        "was_connected": payload.get("was_connected"),
        "is_connected": payload.get("is_connected"),
        "ts": payload.get("ts"),
    }
    try:
        sessions.database["network_transitions"].insert_one(doc)
        if payload.get("session_id"):
            sessions.update_one(
                {"session_id": payload["session_id"], "device_uid": uid},
                {"$inc": {"network_changes": 1}},
            )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/network/transitions")
async def network_transitions(device_uid: str = None, limit: int = 1000):
    q = {"device_uid": device_uid} if device_uid else {}
    rows = list(sessions.database["network_transitions"]
                .find(q, {"_id": 0}).sort("ts", -1).limit(limit))
    return {"ok": True, "count": len(rows), "transitions": rows}
