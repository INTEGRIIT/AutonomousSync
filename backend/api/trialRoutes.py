# backend/api/trialRoutes.py
#
# Endpoints for the app's Trial Mode screen and for exporting labelled
# trials into the collection workbook.

import csv
import io

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.db_trials import (
    EXPORT_COLUMNS,
    start_trial,
    end_trial,
    list_trials,
    delete_trial,
    next_trial_number,
)

router = APIRouter()


@router.post("/trials/start")
async def trials_start(payload: dict):
    if not payload.get("trial_id") or not payload.get("device_uid"):
        return {"ok": False, "error": "trial_id and device_uid required"}

    # The member label arrives from the client and nothing stops an
    # operator selecting the wrong one. device_uid cannot be spoofed
    # from the UI, so where the device record carries an assigned
    # member we use that and record the discrepancy. Otherwise a
    # mis-tap at the start of a session silently files one operator's
    # trials under another's name, and the error is only visible at
    # analysis time.
    try:
        from backend.api.adminRoutes import devices as _devices
        rec = _devices.find_one({"device_uid": payload["device_uid"]},
                                {"_id": 0, "research_member": 1})
        assigned = (rec or {}).get("research_member")
        claimed = payload.get("member")
        if assigned:
            if claimed and claimed != assigned:
                payload["member_claimed"] = claimed
                payload["member_mismatch"] = True
            payload["member"] = assigned
    except Exception as e:
        # A lookup failure must not block a trial mid-collection.
        print("member resolution failed:", e)

    try:
        doc = start_trial(payload)
        return {
            "ok": True,
            "trial_id": doc["trial_id"],
            "member": doc.get("member"),
            "member_mismatch": bool(payload.get("member_mismatch")),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/trials/end")
async def trials_end(payload: dict):
    trial_id = payload.get("trial_id")
    device_uid = payload.get("device_uid")
    if not trial_id or not device_uid:
        return {"ok": False, "error": "trial_id and device_uid required"}
    try:
        rec = end_trial(
            trial_id,
            device_uid,
            packets=payload.get("packets"),
            notes=payload.get("notes"),
        )
        if not rec:
            return {"ok": False, "error": "trial not found"}
        return {"ok": True, "trial": rec}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/trials")
async def trials_list(device_uid: str = None, member: str = None,
                      limit: int = 1000):
    return {"ok": True, "trials": list_trials(device_uid, member, limit)}


@router.get("/trials/next")
async def trials_next(member: str, device_uid: str):
    """Next sequence number for this member, so the app can suggest an id."""
    n = next_trial_number(member, device_uid)
    return {"ok": True, "next": n, "suggested_id": f"{member}-{n:03d}"}


@router.delete("/trials")
async def trials_delete(trial_id: str, device_uid: str):
    n = delete_trial(trial_id, device_uid)
    return {"ok": n > 0, "deleted": n}


@router.get("/trials/export.csv")
async def trials_export(member: str = None, device_uid: str = None):
    """
    CSV in the exact column order of the Trials tabs in
    AutonomousSync_Collection_Workbook.xlsx, so the result pastes
    straight in.
    """
    rows = list_trials(device_uid, member, limit=100000)
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
    name = f"trials_{member or 'all'}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


# =========================================================
# UPLOAD TIMING
#
# Object-store modification time records when a file arrived, not
# when its transfer began, so end-to-end upload latency is only
# observable from the client. Without this, whether a transfer fits
# inside the pre-impact window is an assumption rather than a
# measurement.
# =========================================================

@router.post("/upload/timing")
async def upload_timing(payload: dict):
    from backend.db_trials import trials
    doc = {
        "device_uid": payload.get("device_uid"),
        "snapshot_id": payload.get("snapshot_id"),
        "file_name": payload.get("file_name"),
        "bytes": payload.get("bytes"),
        "started_at": payload.get("started_at"),
        "elapsed_ms": payload.get("elapsed_ms"),
        "ok": payload.get("ok"),
    }
    try:
        trials.database["upload_timings"].insert_one(doc)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/upload/timings")
async def upload_timings(device_uid: str = None, limit: int = 2000):
    from backend.db_trials import trials
    q = {"device_uid": device_uid} if device_uid else {}
    rows = list(trials.database["upload_timings"]
                .find(q, {"_id": 0}).sort("started_at", -1).limit(limit))
    return {"ok": True, "count": len(rows), "timings": rows}
