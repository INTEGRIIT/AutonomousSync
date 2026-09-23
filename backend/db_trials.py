# backend/db_trials.py
#
# Storage for labelled trial records used in the MobiQuitous 2027
# collection run.
#
# A trial record is the GROUND TRUTH for one drop. It is written by the
# operator BEFORE the drop (via the app's Trial Mode screen) and is
# never derived from any classification the system produced. Keeping it
# in a separate collection from `events` makes that separation explicit
# and auditable.
#
# Telemetry packets carry `trial_id`, so analysis joins on that field
# rather than matching timestamps.

from datetime import datetime
from typing import Optional

# Reuse the connection db.py already established rather than opening a
# second client. Every pymongo Collection exposes its parent database.
from backend.db import events_collection

_db = events_collection.database
trials = _db["trials"]

# One trial_id per device. A repeated id means the operator armed twice
# without stopping, or the app was reinstalled mid-session.
trials.create_index([("trial_id", 1), ("device_uid", 1)], unique=True)

# Column order must match the Trials tabs in
# AutonomousSync_Collection_Workbook.xlsx so exports paste in directly.
EXPORT_COLUMNS = [
    "trial_id",
    "device_uid",
    "height_ft",
    "surface",
    "orientation",
    "intended_class",
    "case_type",
    "design",
    "started_at",
    "ended_at",
    "duration_ms",
    "packets",
    "member",
    "member_mismatch",
    "platform",
    "device_model",
    "notes",
    "observed_note",
]


def start_trial(payload: dict) -> dict:
    """
    Record the start of a labelled trial.

    The label (intended_class) and conditions are supplied by the
    operator before the drop. Nothing here reads system output.
    """
    doc = {
        "trial_id": payload.get("trial_id"),
        "device_uid": payload.get("device_uid"),
        "member": payload.get("member"),
        "member_claimed": payload.get("member_claimed"),
        "member_mismatch": bool(payload.get("member_mismatch")),
        "height_ft": payload.get("height_ft"),
        "surface": payload.get("surface"),
        "orientation": payload.get("orientation"),
        "intended_class": payload.get("intended_class"),
        "case_type": payload.get("case_type"),
        "design": payload.get("design", "exploratory"),
        "platform": payload.get("platform"),
        "device_model": payload.get("device_model"),
        "notes": payload.get("notes"),
        "started_at": datetime.utcnow(),
        "ended_at": None,
        "duration_ms": None,
        "packets": None,
        "status": "running",
    }
    trials.update_one(
        {"trial_id": doc["trial_id"], "device_uid": doc["device_uid"]},
        {"$set": doc},
        upsert=True,
    )
    return doc


def end_trial(trial_id: str, device_uid: str, packets: Optional[int] = None,
              notes: Optional[str] = None) -> Optional[dict]:
    rec = trials.find_one({"trial_id": trial_id, "device_uid": device_uid})
    if not rec:
        return None
    now = datetime.utcnow()
    started = rec.get("started_at") or now
    update = {
        "ended_at": now,
        "duration_ms": int((now - started).total_seconds() * 1000),
        "status": "complete",
    }
    if packets is not None:
        update["packets"] = packets
    if notes:
        update["notes"] = notes
    trials.update_one({"_id": rec["_id"]}, {"$set": update})
    return trials.find_one({"_id": rec["_id"]}, {"_id": 0})


def list_trials(device_uid: Optional[str] = None,
                member: Optional[str] = None,
                limit: int = 1000) -> list:
    q = {}
    if device_uid:
        q["device_uid"] = device_uid
    if member:
        q["member"] = member
    return list(
        trials.find(q, {"_id": 0}).sort("started_at", 1).limit(limit)
    )


def delete_trial(trial_id: str, device_uid: str) -> int:
    res = trials.delete_one({"trial_id": trial_id, "device_uid": device_uid})
    return res.deleted_count


def next_trial_number(member: str, device_uid: str) -> int:
    """
    The next unused trial number for this member.

    Counting live records is wrong: deleting a bad trial frees its
    number, the next trial reuses it, and the packet log still holds
    the deleted trial's data under that id. Analysis then merges two
    different drops, which is how a pilot session reported a 488 ms
    lead time that belonged to an earlier, deleted trial.

    A high-water mark that never decreases avoids this. Numbering
    gains gaps where trials were deleted, which is the right trade:
    a gap is visible, a collision is not.
    """
    best = 0
    for rec in trials.find({"member": member}, {"trial_id": 1, "_id": 0}):
        tail = (rec.get("trial_id") or "").rsplit("-", 1)[-1]
        if tail.isdigit():
            best = max(best, int(tail))

    hw_col = trials.database["trial_highwater"]
    hw = hw_col.find_one({"member": member})
    if hw:
        best = max(best, int(hw.get("n", 0)))

    nxt = best + 1
    hw_col.update_one({"member": member}, {"$set": {"n": nxt}}, upsert=True)
    return nxt

