from fastapi import APIRouter, UploadFile, File, Form, Query
import os
import boto3

from backend.storage.s3_service import (
    upload_file_to_s3,
    delete_file_from_s3,
    generate_signed_url,
)

from backend.db import get_device  # 🔥 REQUIRED

router = APIRouter()

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
s3 = boto3.client("s3")


# =========================================================
# 🧠 HELPER: DEVICE → USER
# =========================================================
def get_user_from_device(device_uid: str):
    device = get_device(device_uid)

    if not device:
        raise Exception(f"Device not found: {device_uid}")

    user_id = device.get("user_id")

    if not user_id:
        raise Exception(f"No user_id linked to device: {device_uid}")

    return user_id


# =========================================================
# 📤 UPLOAD FILE
# =========================================================
@router.post("/upload")
async def upload_file(
    device_uid: str = Form(...),
    device_name: str = Form(None),
    user_id: str = Form(None),
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()

        # 🔥 ALWAYS resolve real user
        user = user_id or get_user_from_device(device_uid)

        result = upload_file_to_s3(
            file_bytes=contents,
            filename=file.filename,
            device_uid=device_uid,
            user_id=user,
            device_name=device_name,
            sync_type="manual",
        )

        print(f"📂 FILE UPLOADED → {result['key']}")

        return result

    except Exception as e:
        print("❌ Upload error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# 📥 LIST FILES (WITH METADATA)
# =========================================================
@router.get("/files/{device_uid}")
def list_files(device_uid: str):
    try:
        # 🔥 REAL USER RESOLUTION
        user = device_uid

        prefix = f"users/{user}/devices/{device_uid}/files/"

        print("📂 LIST PREFIX:", prefix)

        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix,
        )

        contents = response.get("Contents", [])

        files = []

        for obj in contents:
            key = obj["Key"]

            try:
                head = s3.head_object(Bucket=S3_BUCKET, Key=key)
                metadata = head.get("Metadata", {})
            except Exception as e:
                print(f"⚠️ head_object failed for {key}: {e}")
                metadata = {}

            files.append({
                "key": key,
                "url": generate_signed_url(key)["url"],  # 🔥 CRITICAL
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
                "uploaded_at": metadata.get("uploaded_at"),
                "sync_type": metadata.get("sync_type"),
                "sync_reason": metadata.get("sync_reason"),
                "device_name": metadata.get("device_name"),
            })

        return {"ok": True, "files": files}

    except Exception as e:
        print("❌ List error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# 🗑️ DELETE FILE (SECURE)
# =========================================================
@router.delete("/delete")
def delete_file(key: str, device_uid: str):
    try:
        user = get_user_from_device(device_uid)

        # 🔐 SECURITY CHECK
        if f"users/{user}/devices/{device_uid}/" not in key:
            return {"ok": False, "error": "Unauthorized"}

        return delete_file_from_s3(key)

    except Exception as e:
        print("❌ Delete error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# 🔗 DOWNLOAD (SIGNED URL, SECURE)
# =========================================================
@router.get("/download")
def download_file(key: str, device_uid: str):
    try:
        user = get_user_from_device(device_uid)

        # 🔐 SECURITY CHECK
        if f"users/{user}/devices/{device_uid}/" not in key:
            return {"ok": False, "error": "Unauthorized"}

        return generate_signed_url(key)

    except Exception as e:
        print("❌ Download error:", e)
        return {"ok": False, "error": str(e)}
