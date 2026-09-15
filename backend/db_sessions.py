# backend/db_sessions.py
#
# Storage for duration-based recording sessions: benign activity and
# energy measurement.
#
# WHY THIS EXISTS SEPARATELY FROM TRIALS
# A trial is an event, a few seconds long, and its label is the class
# of that event. A session is a duration, minutes to hours, and its
# label is the activity being performed throughout. The two need
# different records, but they need the same property: the identifier
# must ride in the telemetry stream so analysis joins on a field
# rather than on a timestamp written down by hand.
#
# Without this, the false-positive rate depends on someone noting a
# start time in a spreadsheet and the packets being matched to it
# afterwards. That is the provenance failure that made the earlier
# corpus unreconcilable, and it applies to the benign hours exactly
# as it applied to the drops.

from datetime import datetime
from typing import Optional

from backend.db import events_collection

_db = events_collection.database
sessions = _db["sessions"]

sessions.create_index([("session_id", 1), ("device_uid", 1)], unique=True)

EXPORT_COLUMNS = [
    "session_id",
    "device_uid",
    "member",
    "session_type",
    "started_at",
    "ended_at",
    "duration_s",
    "packets",
    "battery_start",
    "battery_end",
    "battery_drop_pct",
    "drain_pct_per_hour",
    "network_type",
    "network_changes",
    "platform",
    "device_model",
    "notes",
]


def start_session(payload: dict) -> dict:
    doc = {
        "session_id": payload.get("session_id"),
        "device_uid": payload.get("device_uid"),
        "member": payload.get("member"),
        "session_type": payload.get("session_type"),
        "platform": payload.get("platform"),
        "device_model": payload.get("device_model"),
        "battery_start": payload.get("battery_start"),
        "network_type": payload.get("network_type"),
        "notes": payload.get("notes"),
        "started_at": datetime.utcnow(),
        "ended_at": None,
        "duration_s": None,
        "packets": None,
        "battery_end": None,
        "network_changes": 0,
        "status": "running",
    }
    sessions.update_one(
        {"session_id": doc["session_id"], "device_uid": doc["device_uid"]},
        {"$set": doc},
        upsert=True,
    )
    return doc


def end_session(session_id: str, device_uid: str,
                packets: Optional[int] = None,
                battery_end: Optional[float] = None,
                network_changes: Optional[int] = None,
                notes: Optional[str] = None) -> Optional[dict]:
    rec = sessions.find_one({"session_id": session_id,
                             "device_uid": device_uid})
    if not rec:
        return None

    now = datetime.utcnow()
    started = rec.get("started_at") or now
    dur = (now - started).total_seconds()

    update = {"ended_at": now, "duration_s": round(dur, 1),
              "status": "complete"}
    if packets is not None:
        update["packets"] = packets
    if network_changes is not None:
        update["network_changes"] = network_changes
    if notes:
        update["notes"] = notes

    if battery_end is not None:
        update["battery_end"] = battery_end
        b0 = rec.get("battery_start")
        if b0 is not None and dur > 0:
            drop = (b0 - battery_end) * 100.0
            update["battery_drop_pct"] = round(drop, 2)
            # Only meaningful over a long enough window: platform
            # battery reporting is quantised coarsely enough that a
            # short session is dominated by quantisation noise.
            if dur >= 900:
                update["drain_pct_per_hour"] = round(drop / (dur / 3600.0), 3)

    sessions.update_one({"_id": rec["_id"]}, {"$set": update})
    return sessions.find_one({"_id": rec["_id"]}, {"_id": 0})


def list_sessions(device_uid: Optional[str] = None,
                  member: Optional[str] = None,
                  session_type: Optional[str] = None,
                  limit: int = 1000) -> list:
    q = {}
    if device_uid:
        q["device_uid"] = device_uid
    if member:
        q["member"] = member
    if session_type:
        q["session_type"] = session_type
    return list(sessions.find(q, {"_id": 0})
                .sort("started_at", 1).limit(limit))


def delete_session(session_id: str, device_uid: str) -> int:
    return sessions.delete_one({"session_id": session_id,
                                "device_uid": device_uid}).deleted_count


def next_session_number(member: str) -> int:
    best = 0
    for rec in sessions.find({"member": member}, {"session_id": 1, "_id": 0}):
        sid = rec.get("session_id") or ""
        tail = sid.rsplit("-", 1)[-1]
        if tail.isdigit():
            best = max(best, int(tail))
    return best + 1
