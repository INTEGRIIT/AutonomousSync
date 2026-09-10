from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# ---------------------------------------------------
# 🔐 LOAD ENV
# ---------------------------------------------------

load_dotenv()  # loads backend/.env

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise Exception("❌ MONGO_URI not found in .env")

# ---------------------------------------------------
# 🔌 CONNECTION
# ---------------------------------------------------

try:
    client = MongoClient(MONGO_URI)
    client.admin.command("ping")
    print("✅ MongoDB connected successfully")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    raise e

# ---------------------------------------------------
# 🧠 DATABASE
# ---------------------------------------------------

db = client["autonomous_sync"]
devices = db["devices"]

# ---------------------------------------------------
# 🛠️ HELPERS
# ---------------------------------------------------

from datetime import datetime

def upsert_device(device_uid, device_name, push_token, platform, preferences=None):
    devices.update_one(
        {"device_uid": device_uid},
        {
            "$set": {
                "device_name": device_name,
                "push_token": push_token,
                "platform": platform,
                "preferences": preferences or {},
                "last_seen": datetime.utcnow(),
                "is_active": True,
            }
        },
        upsert=True,
    )