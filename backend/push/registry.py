# backend/push/registry.py

import time
from typing import Optional

_DEVICES: dict[str, dict] = {}


def is_valid_apns_token(token: str) -> bool:
    return (
        isinstance(token, str)
        and len(token) >= 50
        and all(c in "0123456789abcdef" for c in token.lower())
    )


def register_device(device_id: str, token: str, platform: Optional[str] = None):
    """
    Register or update a device APNs token.

    - APNs only
    - Overwrites existing token safely
    - Tracks last_seen for debugging
    """

    if not is_valid_apns_token(token):
        raise ValueError("Invalid APNs token")

    if platform and platform != "ios":
        raise ValueError("Only iOS APNs tokens are supported")

    _DEVICES[device_id] = {
        "token": token,
        "platform": "ios",
        "last_seen": time.time(),
    }

    print(
        f"[push] registered device={device_id} "
        f"platform=ios token_len={len(token)}"
    )


def get_device(device_id: str) -> Optional[dict]:
    return _DEVICES.get(device_id)


def all_devices():
    return _DEVICES