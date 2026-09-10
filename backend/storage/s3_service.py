import boto3
import os
import mimetypes
from uuid import uuid4
from datetime import datetime, timezone

# =========================================================
# 🌍 ENV CONFIG
# =========================================================

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("AWS_REGION")

if not S3_BUCKET:
    raise Exception("S3_BUCKET_NAME not set")

if not S3_REGION:
    raise Exception("AWS_REGION not set")

s3 = boto3.client("s3")


# =========================================================
# 🧠 HELPERS
# =========================================================

def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def sanitize_filename(name: str):
    return name.replace("/", "_").replace(" ", "_")


# =========================================================
# 🧱 PATH BUILDER (DEVICE = PRIMARY IDENTITY)
# =========================================================

def build_s3_key(
    kind: str,
    device_uid: str,
    filename=None,
    snapshot_id=None,
    user_id=None
):
    # 🔥 CRITICAL FIX: device_uid is ALWAYS the fallback identity
    user_id = user_id or device_uid
    device_uid = device_uid or "unknown_device"

    base = f"users/{user_id}/devices/{device_uid}"

    if kind == "file":
        return f"{base}/files/{filename}"

    if kind == "snapshot":
        return f"{base}/snapshots/{snapshot_id}.json"

    if kind == "device_meta":
        return f"{base}/metadata/device.json"

    raise ValueError(f"Invalid S3 kind: {kind}")


# =========================================================
# 📤 FILE UPLOAD (ENHANCED METADATA)
# =========================================================

def upload_file_to_s3(
    file_bytes,
    filename,
    device_uid,
    user_id=None,
    device_name=None,
    sync_type="manual",          # 🔥 manual | emergency | auto
    sync_reason=None             # 🔥 free_fall, impact, etc.
):
    try:
        filename = sanitize_filename(filename)

        unique_name = f"{uuid4()}_{filename}"

        key = build_s3_key(
            kind="file",
            device_uid=device_uid,
            filename=unique_name,
            user_id=user_id,
        )

        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        now = _utc_now_iso()

        # =========================================================
        # 🔥 ELITE METADATA (USED BY FILE MANAGER + SYNC ENGINE)
        # =========================================================

        metadata = {
            "original_name": filename,
            "device_uid": str(device_uid),
            "device_name": str(device_name or "unknown"),
            "user_id": str(user_id or device_uid),

            # 📤 USER ACTION
            "uploaded_at": now,

            # 🔄 SYSTEM SYNC CONTEXT
            "sync_type": sync_type,        # manual | emergency
        }

        if sync_reason:
            metadata["sync_reason"] = str(sync_reason)

        # =========================================================
        # 🚀 UPLOAD
        # =========================================================

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            Metadata=metadata,
        )

        url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"

        print(f"📂 file uploaded → {key}")
        print(f"📦 metadata → {metadata}")

        return {
            "ok": True,
            "key": key,
            "url": url,
            "name": filename,
            "uploaded_at": now,
            "sync_type": sync_type,
        }

    except Exception as e:
        print("❌ file upload error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# 🧠 SNAPSHOT UPLOAD (EMERGENCY SYSTEM)
# =========================================================

def upload_snapshot_to_s3(
    snapshot_json: str,
    device_uid: str,
    snapshot_id: str,
    user_id=None,
    device_name=None,
    sync_reason=None
):
    try:
        key = build_s3_key(
            kind="snapshot",
            device_uid=device_uid,
            snapshot_id=snapshot_id,
            user_id=user_id,
        )

        now = _utc_now_iso()

        metadata = {
            "device_uid": str(device_uid),
            "device_name": str(device_name or "unknown"),
            "snapshot_id": str(snapshot_id),
            "user_id": str(user_id or device_uid),

            # 🔄 SYSTEM EVENT
            "uploaded_at": now,
            "sync_type": "emergency",
        }

        if sync_reason:
            metadata["sync_reason"] = str(sync_reason)

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=snapshot_json.encode("utf-8"),
            ContentType="application/json",
            Metadata=metadata,
        )

        url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"

        print(f"🧠 snapshot uploaded → {key}")

        return {
            "ok": True,
            "key": key,
            "url": url,
        }

    except Exception as e:
        print("❌ snapshot upload error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# 📦 DEVICE METADATA (PROFILE + PREFS)
# =========================================================

def upload_device_metadata_to_s3(
    device_uid,
    user_id=None,
    device_name=None,
    platform=None,
    preferences=None
):
    try:
        import json

        key = build_s3_key(
            kind="device_meta",
            device_uid=device_uid,
            user_id=user_id,
        )

        payload = {
            "device_uid": device_uid,
            "device_name": device_name or "unknown",
            "platform": platform or "unknown",
            "preferences": preferences or {},
            "user_id": user_id or device_uid,
            "updated_at": _utc_now_iso(),
        }

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )

        print(f"📦 device metadata saved → {key}")

        return {"ok": True, "key": key}

    except Exception as e:
        print("❌ device metadata error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# 🗑️ DELETE FILE
# =========================================================

def delete_file_from_s3(key: str):
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=key)
        print(f"🗑️ deleted → {key}")
        return {"ok": True}
    except Exception as e:
        print("❌ delete error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# 🔗 SIGNED URL
# =========================================================

def generate_signed_url(key: str, expires_in=3600):
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
        return {"ok": True, "url": url}
    except Exception as e:
        print("❌ signed url error:", e)
        return {"ok": False, "error": str(e)}