# backend/api/verifyRoutes.py
#
# Verification that an emergency snapshot actually reached object
# storage.
#
# WHY THIS EXISTS
# Reviewer 3's first point was that the 2026 evaluation demonstrated a
# workflow running, not data surviving: copying a file to another
# directory on the same handset protects against nothing, and upload
# before impact was never evaluated. These endpoints let the collection
# run record, per trial, whether the object is really in the bucket and
# how large it is — the difference between "the sync path executed" and
# "the data exists somewhere the phone isn't".

import os

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter

router = APIRouter()

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def _client():
    return boto3.client("s3", region_name=AWS_REGION)


@router.get("/verify/object")
async def verify_object(key: str):
    """HEAD one object. Returns whether it exists, its size and mtime."""
    if not S3_BUCKET:
        return {"ok": False, "error": "S3_BUCKET_NAME not configured"}
    try:
        head = _client().head_object(Bucket=S3_BUCKET, Key=key)
        return {
            "ok": True,
            "exists": True,
            "key": key,
            "size_bytes": head.get("ContentLength"),
            "size_kb": round((head.get("ContentLength") or 0) / 1024, 1),
            "last_modified": head["LastModified"].isoformat(timespec="seconds")
            if head.get("LastModified") else None,
            "content_type": head.get("ContentType"),
        }
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            return {"ok": True, "exists": False, "key": key}
        return {"ok": False, "error": f"{code}: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/verify/snapshot")
async def verify_snapshot(snapshot_id: str, prefix: str = ""):
    """
    List everything stored under a snapshot id.

    Use this per trial: given the snapshot_id the app reported, confirm
    the objects are really there and record their sizes.
    """
    if not S3_BUCKET:
        return {"ok": False, "error": "S3_BUCKET_NAME not configured"}
    try:
        p = f"{prefix.rstrip('/')}/{snapshot_id}" if prefix else snapshot_id
        resp = _client().list_objects_v2(Bucket=S3_BUCKET, Prefix=p)
        objs = [
            {
                "key": o["Key"],
                "size_bytes": o["Size"],
                "size_kb": round(o["Size"] / 1024, 1),
                "last_modified": o["LastModified"].isoformat(timespec="seconds"),
            }
            for o in resp.get("Contents", [])
        ]
        return {
            "ok": True,
            "snapshot_id": snapshot_id,
            "found": len(objs),
            "total_kb": round(sum(o["size_bytes"] for o in objs) / 1024, 1),
            "objects": objs,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/verify/recent")
async def verify_recent(limit: int = 25, prefix: str = ""):
    """Most recent objects in the bucket — a quick 'is anything arriving'."""
    if not S3_BUCKET:
        return {"ok": False, "error": "S3_BUCKET_NAME not configured"}
    try:
        # list_objects_v2 caps at 1000 keys per call, so page through
        # the whole bucket rather than reporting a truncated view.
        c = _client()
        kw = {"Bucket": S3_BUCKET, "MaxKeys": 1000}
        if prefix:
            kw["Prefix"] = prefix
        contents = []
        token = None
        while True:
            if token:
                kw["ContinuationToken"] = token
            resp = c.list_objects_v2(**kw)
            contents.extend(resp.get("Contents", []))
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
        objs = sorted(
            contents,
            key=lambda o: o["LastModified"],
            reverse=True,
        )[:limit]
        return {
            "ok": True,
            "count": len(objs),
            "objects": [
                {
                    "key": o["Key"],
                    "size_kb": round(o["Size"] / 1024, 1),
                    "last_modified": o["LastModified"].isoformat(
                        timespec="seconds"),
                }
                for o in objs
            ],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
