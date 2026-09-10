import os
import time
import httpx
import jwt

from backend.db import get_device
from backend.push.fcm_sender import send_fcm_push  # 🔥 ANDROID SUPPORT

# =========================================================
# ENV CONFIG
# =========================================================

APNS_KEY_ID = os.environ["APNS_KEY_ID"]
APNS_TEAM_ID = os.environ["APNS_TEAM_ID"]
APNS_TOPIC = os.environ["APNS_TOPIC"]
APNS_KEY_PATH = os.environ.get("APNS_KEY_PATH", "backend/apns/AuthKey.p8")

APNS_USE_SANDBOX = os.environ.get("APNS_USE_SANDBOX", "true").lower() == "true"

APNS_URL = (
    "https://api.sandbox.push.apple.com"
    if APNS_USE_SANDBOX
    else "https://api.push.apple.com"
)

# =========================================================
# JWT CACHE
# =========================================================

_cached_jwt = None
_cached_jwt_issued_at = 0
JWT_TTL_SECONDS = 50 * 60


def _get_jwt() -> str:
    global _cached_jwt, _cached_jwt_issued_at

    now = int(time.time())

    if _cached_jwt and (now - _cached_jwt_issued_at) < JWT_TTL_SECONDS:
        return _cached_jwt

    with open(APNS_KEY_PATH, "r", encoding="utf-8") as f:
        secret = f.read()

    headers = {
        "alg": "ES256",
        "kid": APNS_KEY_ID,
    }

    payload = {
        "iss": APNS_TEAM_ID,
        "iat": now,
    }

    token = jwt.encode(payload, secret, algorithm="ES256", headers=headers)

    _cached_jwt = token
    _cached_jwt_issued_at = now

    return token


# =========================================================
# 🚀 MAIN PUSH ROUTER (FINAL)
# =========================================================

def send_push(
    device_uid: str,
    title: str | None = None,
    body: str | None = None,
    data: dict | None = None,
    silent: bool = False,
) -> bool:

    record = get_device(device_uid)

    if not record:
        print(f"[push] no device registered: {device_uid}")
        return False

    push_token = record.get("push_token")
    device_name = record.get("device_name")
    platform = (record.get("platform") or "").lower()

    if not push_token:
        print(f"[push] missing push_token for device_uid={device_uid}")
        return False

    print(f"📲 PUSH ROUTER → platform={platform} device={device_uid}")

    # =========================================================
    # 🍎 iOS → APNs
    # =========================================================
    if platform == "ios":

        jwt_token = _get_jwt()
        extra_data = data or {}

        # 🔥 FORCE ACTION
        if "action" not in extra_data:
            extra_data["action"] = "UPLOAD"

        if silent:
            payload = {
                "aps": {"content-available": 1},
                **extra_data,
            }
            push_type = "background"
            priority = "5"
            expiration_seconds = 300
        else:
            payload = {
                "aps": {
                    "alert": {
                        "title": title or "Autonomous Sync",
                        "body": body or "Backup triggered",
                    },
                    "sound": "default",
                    "badge": 1,
                },
                **extra_data,
            }
            push_type = "alert"
            priority = "10"
            expiration_seconds = 3600

        headers = {
            "authorization": f"bearer {jwt_token}",
            "apns-topic": APNS_TOPIC,
            "apns-push-type": push_type,
            "apns-priority": priority,
            "apns-expiration": str(int(time.time()) + expiration_seconds),
            "apns-collapse-id": "autonomous-sync-alert",
        }

        url = f"{APNS_URL}/3/device/{push_token}"

        print("🔥 APNS CONFIG:", {
            "url": APNS_URL,
            "sandbox": APNS_USE_SANDBOX,
        })

        try:
            with httpx.Client(http2=True, timeout=8.0, trust_env=False) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

            apns_id = response.headers.get("apns-id")

            print("📡 APNS RESPONSE:", {
                "status": response.status_code,
                "apns_id": apns_id,
                "body": response.text,
            })

            if response.status_code == 200:
                print(f"✅ APNS DELIVERED → {device_uid}")
                return True

            print(f"❌ APNS FAILED → {response.text}")
            return False

        except Exception as e:
            print(f"❌ APNS EXCEPTION: {e}")
            return False

    # =========================================================
    # 🤖 ANDROID → FCM
    # =========================================================
    elif platform == "android":

        print(f"🔥 FCM SEND → {device_uid}")

        return send_fcm_push(
            token=push_token,
            title=title or "Autonomous Sync",
            body=body or "Backup triggered",
            data=data or {},
        )

    # =========================================================
    # ❌ UNKNOWN PLATFORM
    # =========================================================
    else:
        print(f"❌ UNKNOWN PLATFORM: {platform}")
        return False
