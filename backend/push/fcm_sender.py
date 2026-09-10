# backend/push/fcm_sender.py

import firebase_admin
from firebase_admin import credentials, messaging
import os

# =========================================================
# LOAD PATH FROM ENV
# =========================================================

FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH")

if not FIREBASE_CRED_PATH:
    raise ValueError("❌ FIREBASE_CRED_PATH not set in .env")

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)


# =========================================================
# SEND PUSH
# =========================================================

def send_fcm_push(token: str, title: str, body: str, data: dict = None):

    if not token:
        print("❌ No FCM token provided")
        return False

    try:
        message = messaging.Message(
            token=token,

            notification=messaging.Notification(
                title=title,
                body=body,
            ),

            data={k: str(v) for k, v in (data or {}).items()},

            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="default"
                )
            )
        )

        response = messaging.send(message)

        print(f"✅ FCM SENT: {response}")
        return True

    except Exception as e:
        print(f"❌ FCM ERROR: {e}")
        return False
