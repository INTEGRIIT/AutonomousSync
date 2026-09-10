from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise Exception("MONGO_URI not found in .env")

# =========================================================
# CONNECTION
# =========================================================

try:
    client = MongoClient(MONGO_URI)
    client.admin.command("ping")
    print("[DB] MongoDB connected")
except Exception as e:
    print("[DB] Mongo connection failed:", e)
    raise e

# =========================================================
# DATABASE
# =========================================================

db = client["autonomous_sync"]

devices_collection = db["devices"]
events_collection = db["events"]
snapshots_collection = db["snapshots"]
preferences_collection = db["preferences"]  # optional future use

# =========================================================
# INDEXES (CRITICAL FOR SCALE)
# =========================================================

devices_collection.create_index("device_uid", unique=True)
devices_collection.create_index("user_id")
devices_collection.create_index("last_seen")

events_collection.create_index("device_uid")
events_collection.create_index("timestamp")
events_collection.create_index("type")

snapshots_collection.create_index("device_uid")
snapshots_collection.create_index("snapshot_id", unique=True)
snapshots_collection.create_index("created_at")

preferences_collection.create_index("device_uid", unique=True)

# =========================================================
# DEVICE HELPERS (FIXED)
# =========================================================

def upsert_device(
    device_uid,
    device_name=None,
    push_token=None,
    platform=None,
    preferences=None,
    user_id=None,
):
    """
    SAFE UPSERT:
    - Will NOT overwrite fields with None
    - Will NOT crash if partial data is passed
    - Supports preferences properly
    """

    update_doc = {
        "device_uid": device_uid,
        "last_seen": datetime.utcnow(),
        "is_active": True,
    }

    if device_name is not None:
        update_doc["device_name"] = device_name

    if push_token is not None:
        update_doc["push_token"] = push_token

    if platform is not None:
        update_doc["platform"] = platform

    if user_id is not None:
        update_doc["user_id"] = user_id

    # 🔥 FIX: ACTUALLY STORE PREFERENCES
    if preferences is not None:
        update_doc["preferences"] = preferences

    devices_collection.update_one(
        {"device_uid": device_uid},   # MUST MATCH get_device
        {"$set": update_doc},
        upsert=True,
    )

    print(f"✅ DEVICE UPSERTED: {device_uid}")


def get_device(device_uid):
    device = devices_collection.find_one({"device_uid": device_uid})
    if not device:
        return None
    device.pop("_id", None)
    return device


def get_all_devices():
    return list(devices_collection.find({}, {"_id": 0}))


def deactivate_device(device_uid):
    devices_collection.update_one(
        {"device_uid": device_uid},
        {
            "$set": {
                "is_active": False,
                "last_seen": datetime.utcnow(),
            }
        },
    )


def get_devices_by_user(user_id):
    return list(
        devices_collection.find(
            {"user_id": user_id, "is_active": True},
            {"_id": 0},
        )
    )

# =========================================================
# EVENT HELPERS
# =========================================================

def insert_event(event: dict):
    event["timestamp"] = datetime.utcnow()
    events_collection.insert_one(event)


def get_recent_events(limit=50):
    return list(
        events_collection.find({}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )


def get_events_by_device(device_uid, limit=50):
    return list(
        events_collection.find(
            {"device_uid": device_uid},
            {"_id": 0}
        )
        .sort("timestamp", -1)
        .limit(limit)
    )

# =========================================================
# SNAPSHOT HELPERS
# =========================================================

def insert_snapshot(snapshot: dict):
    snapshot["created_at"] = datetime.utcnow()
    snapshots_collection.insert_one(snapshot)


def get_recent_snapshots(limit=50):
    return list(
        snapshots_collection.find({}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )


def get_snapshots_by_device(device_uid, limit=50):
    return list(
        snapshots_collection.find(
            {"device_uid": device_uid},
            {"_id": 0}
        )
        .sort("created_at", -1)
        .limit(limit)
    )

# =========================================================
# USER PREFERENCES (OPTIONAL SEPARATE STORAGE)
# =========================================================

def set_preferences(device_uid, preferences: dict):
    preferences_collection.update_one(
        {"device_uid": device_uid},
        {
            "$set": {
                "preferences": preferences,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def get_preferences(device_uid):
    pref = preferences_collection.find_one(
        {"device_uid": device_uid},
        {"_id": 0}
    )
    return pref if pref else None
