# backend/push/sender.py

import os
import time
import httpx
import jwt
from backend.push.registry import get_device

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

# ---------------------------------------------------------
# JWT CACHE (APPLE RECOMMENDED)
# ---------------------------------------------------------

_cached_jwt = None
_cached_jwt_issued_at = 0
JWT_TTL = 50 * 60  # 50 minutes


def _get_jwt() -> str:
    global _cached_jwt, _cached_jwt_issued_at

    now = int(time.time())
    if _cached_jwt and now - _cached_jwt_issued_at < JWT_TTL:
        return _cached_jwt

    with open(APNS_KEY_PATH, "r") as f:
        secret = f.read()

    headers = {"alg": "ES256", "kid": APNS_KEY_ID}
    payload = {"iss": APNS_TEAM_ID, "iat": now}

    _cached_jwt = jwt.encode(payload, secret, algorithm="ES256", headers=headers)
    _cached_jwt_issued_at = now
    return _cached_jwt


# ---------------------------------------------------------
# SEND PUSH
# ---------------------------------------------------------

def send_push(
    device_uid: str,
    title: str | None,
    body: str | None,
    data: dict | None = None,
    silent: bool = False,
) -> dict:
    
    record = get_device(device_uid)
    if not record:
        print(f"[push] no device registered: {device_uid}")
        return False

    token = record["token"]
    jwt_token = _get_jwt()

    if silent:
        payload = {
            "aps": {
                "content-available": 1
            },
            "custom": data or {},
        }
        push_type = "background"
        priority = "5"
    else:
        payload = {
            "aps": {
                "alert": {"title": title, "body": body},
                "sound": "default",
            },
            "custom": data or {},
        }
        push_type = "alert"
        priority = "10"

    headers = {
        "authorization": f"bearer {jwt_token}",
        "apns-topic": APNS_TOPIC,
        "apns-push-type": push_type,
        "apns-priority": priority,
        "apns-expiration": str(int(time.time()) + (300 if silent else 3600)),
        "apns-collapse-id": device_uid,
    }

    try:
        with httpx.Client(http2=True, timeout=5, trust_env=False) as client:
            r = client.post(
                f"{APNS_URL}/3/device/{token}",
                headers=headers,
                json=payload,
            )

        apns_id = r.headers.get("apns-id")

        if r.status_code == 200:
            print(f"[push] delivered ✔ apns-id={apns_id}")
            return True

        print(
            f"[push] APNS ERROR status={r.status_code} "
            f"apns-id={apns_id} body={r.text}"
        )
        return False

    except Exception as e:
        print("[push] exception:", e)
        return False