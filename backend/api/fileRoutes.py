from fastapi import APIRouter, UploadFile, File, Form, Query
import os
import boto3

from backend.storage.s3_service import (
    upload_file_to_s3,
    delete_file_from_s3,
    generate_signed_url,
)

router = APIRouter()

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
s3 = boto3.client("s3")


# =========================================================
# 📤 UPLOAD FILE (FIXED IDENTITY)
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

        # 🔥 CRITICAL FIX: device_uid fallback
        user = user_id or device_uid

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
# 📥 LIST FILES (FIXED + TIMESTAMPS)
# =========================================================
@router.get("/files/{device_uid}")
def list_files(
    device_uid: str,
    user_id: str = Query(None)
):
    try:
        user = user_id or device_uid

        prefix = f"users/{user}/devices/{device_uid}/files/"

        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix,
        )

        contents = response.get("Contents", [])

        files = [
            {
                "key": obj["Key"],
                "size": obj["Size"],

                # 🔥 THIS FIXES YOUR "Synced: N/A"
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in contents
        ]

        return {"ok": True, "files": files}

    except Exception as e:
        print("❌ List error:", e)
        return {"ok": False, "error": str(e)}


# =========================================================
# 🗑️ DELETE FILE
# =========================================================
@router.delete("/delete")
def delete_file(key: str):
    return delete_file_from_s3(key)


# =========================================================
# 🔗 DOWNLOAD (SIGNED URL)
# =========================================================
@router.get("/download")
def download_file(key: str):
    return generate_signed_url(key)