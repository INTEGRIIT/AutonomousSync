# backend/push/registry.py

import time
from typing import Optional, Dict

# In-memory registry (can swap with Redis/DB later)
_DEVICES: Dict[str, dict] = {}


# --------------------------------------------------
# TOKEN VALIDATION (PRODUCTION-SAFE)
# --------------------------------------------------

def is_valid_apns_token(token: str) -> bool:
    """
    Production-safe APNs token validation.

    We DO NOT enforce strict hex because:
    - Expo / bridges can alter formatting
    - Future Apple formats may change
    - We prioritize reliability over strictness

    We only enforce:
    - string
    - reasonable length
    """

    if not isinstance(token, str):
        return False

    token = token.strip()

    # APNs tokens are typically 64+ chars
    if len(token) < 32:
        return False

    return True


# --------------------------------------------------
# REGISTER DEVICE
# --------------------------------------------------

def register_device(
    device_uid: str,
    device_name: str,
    token: str,
    platform: Optional[str] = None,
):
    """
    Register or update a device.

    Features:
    - Safe overwrite
    - Tracks last_seen
    - Logs everything for debugging
    """

    if not device_uid:
        raise ValueError("Missing device_uid")

    if not device_name:
        raise ValueError("Missing device_name")

    if not is_valid_apns_token(token):
        print(f"[push][ERROR] invalid token received: {token}")
        raise ValueError("Invalid APNs token")

    if platform and platform != "ios":
        raise ValueError("Only iOS APNs tokens are supported")

    existing = _DEVICES.get(device_uid)

    # --------------------------------------------------
    # UPDATE OR CREATE
    # --------------------------------------------------

    _DEVICES[device_uid] = {
        "device_uid": device_uid,
        "device_name": device_name.strip(),
        "token": token.strip(),
        "platform": "ios",
        "last_seen": time.time(),
    }

    if existing:
        print(
            f"[push][UPDATE] uid={device_uid} "
            f"name={device_name} "
            f"token_len={len(token)}"
        )
    else:
        print(
            f"[push][NEW] uid={device_uid} "
            f"name={device_name} "
            f"token_len={len(token)}"
        )


# --------------------------------------------------
# FETCH DEVICE
# --------------------------------------------------

def get_device(device_uid: str) -> Optional[dict]:
    device = _DEVICES.get(device_uid)

    if not device:
        print(f"[push] no device registered: {device_uid}")
        return None

    return device


# --------------------------------------------------
# LIST DEVICES (DEBUG)
# --------------------------------------------------

def all_devices():
    return _DEVICES


# --------------------------------------------------
# DEBUG PRINT (VERY IMPORTANT FOR YOU)
# --------------------------------------------------

def debug_dump_devices():
    print("\n=== REGISTERED DEVICES ===")

    if not _DEVICES:
        print("No devices registered")
        return

    for uid, d in _DEVICES.items():
        print(
            f"uid={uid} | name={d['device_name']} | "
            f"token_len={len(d['token'])} | last_seen={int(d['last_seen'])}"
        )

    print("===========================\n")
