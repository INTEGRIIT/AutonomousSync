"""
BackupService
--------------------------------------------------
Elite Production Snapshot Persistence Layer

- Atomic writes
- Preference-aware filtering
- AI-ready schema
- Multi-device scalable
- S3-first (with local fallback)
"""

import os
import uuid
import json
import time
import re
import hashlib
from typing import Dict, Any

from backend.db import get_preferences
from backend.storage.s3_service import upload_snapshot_to_s3


class BackupService:
    def __init__(self, base_path: str = "logs/snapshots"):
        self.base_path = base_path

        os.makedirs(self.base_path, exist_ok=True)

        if not os.access(self.base_path, os.W_OK):
            raise PermissionError(f"[snapshot] ❌ no write access: {self.base_path}")

    # --------------------------------------------------
    # SAFETY
    # --------------------------------------------------

    def _safe_filename(self, s: str) -> str:
        s = (s or "").strip()
        s = re.sub(r"[^a-zA-Z0-9._-]", "_", s)
        return s[:120] or "unknown"

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    def store_snapshot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            snapshot_id = self._generate_snapshot_id()

            device_uid = payload.get("device_uid") or "unknown"

            # 🔥 ensure user_id always exists (CRITICAL)
            payload["user_id"] = payload.get("user_id") or "test_user_1"

            snapshot = self._build_snapshot_artifact(snapshot_id, payload)

            # 🔥 Apply preferences
            snapshot = self._apply_preferences(snapshot, device_uid)

            # 🔥 Persist
            self._persist_snapshot(snapshot)

            return {
                "ok": True,
                "snapshot_id": snapshot_id,
                "timestamp": snapshot["timestamp"],
                "path": snapshot["_meta"].get("path"),
                "s3_url": snapshot["_meta"].get("url"),
                "s3_key": snapshot["_meta"].get("s3_key"),
                "storage": snapshot["_meta"].get("storage"),
            }

        except Exception as e:
            print(f"[snapshot] ❌ error: {e}")
            return {
                "ok": False,
                "snapshot_id": None,
                "error": str(e),
            }

    # --------------------------------------------------
    # INTERNAL
    # --------------------------------------------------

    def _generate_snapshot_id(self) -> str:
        return str(uuid.uuid4())

    def _build_snapshot_artifact(
        self, snapshot_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        timestamp = int(time.time())

        checksum = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        return {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "device_uid": payload.get("device_uid"),
            "user_id": payload.get("user_id"),  # 🔥 CRITICAL FIX

            # -----------------------------
            # STATE
            # -----------------------------
            "state": payload.get("state"),
            "type": payload.get("type"),
            "reason": payload.get("reason"),
            "priority": payload.get("priority"),

            # -----------------------------
            # SIGNAL DATA
            # -----------------------------
            "features": payload.get("features"),
            "temporal": payload.get("temporal"),
            "water": payload.get("water"),

            # -----------------------------
            # TELEMETRY
            # -----------------------------
            "telemetry": payload.get("telemetry", {}),

            # -----------------------------
            # DECISION TRACE
            # -----------------------------
            "decision": payload.get("decision", {}),

            # -----------------------------
            # CONTEXT
            # -----------------------------
            "context": payload.get("context", {}),

            # -----------------------------
            # VERSIONING
            # -----------------------------
            "schema_version": "v2",
            "system_version": payload.get("system_version", "v1"),

            # -----------------------------
            # INTEGRITY
            # -----------------------------
            "checksum": checksum,

            # -----------------------------
            # META
            # -----------------------------
            "_meta": {
                "created_at": timestamp,
                "storage": None,
                "path": None,
                "s3_key": None,
                "url": None,
                "compressed": False,
                "size_bytes": None,
            },
        }

    def _persist_snapshot(self, snapshot: Dict[str, Any]) -> None:
        snapshot_id = snapshot["snapshot_id"]

        device_uid = self._safe_filename(snapshot.get("device_uid", "unknown"))
        user_id = snapshot.get("user_id") or "anonymous"

        try:
            # --------------------------------------------------
            # SIZE PROTECTION
            # --------------------------------------------------
            MAX_SIZE_BYTES = 5 * 1024 * 1024

            raw_json = json.dumps(snapshot)
            if len(raw_json.encode("utf-8")) > MAX_SIZE_BYTES:
                print("[snapshot] ⚠️ too large — trimming heavy fields")
                snapshot.pop("features", None)
                snapshot.pop("temporal", None)

            snapshot_json = json.dumps(snapshot)

            # --------------------------------------------------
            # ☁️ PRIMARY: S3
            # --------------------------------------------------
            result = upload_snapshot_to_s3(
                snapshot_json=snapshot_json,
                device_uid=device_uid,
                snapshot_id=snapshot_id,
                user_id=user_id,
            )

            if not result.get("ok"):
                raise Exception(result.get("error"))

            snapshot["_meta"]["storage"] = "s3"
            snapshot["_meta"]["s3_key"] = result["key"]
            snapshot["_meta"]["url"] = result["url"]
            snapshot["_meta"]["path"] = None  # 🔥 important

            print(f"[snapshot] ☁️ uploaded → {result['key']}")

        except Exception as e:
            print(f"[snapshot] ❌ S3 FAILED → fallback local:", e)

            # --------------------------------------------------
            # 💾 FALLBACK LOCAL
            # --------------------------------------------------
            device_path = os.path.join(self.base_path, device_uid)
            os.makedirs(device_path, exist_ok=True)

            file_path = os.path.join(device_path, f"{snapshot_id}.json")
            temp_path = f"{file_path}.tmp"

            snapshot["_meta"]["path"] = file_path

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, file_path)

            size = os.path.getsize(file_path)
            snapshot["_meta"]["size_bytes"] = size
            snapshot["_meta"]["storage"] = "local_fallback"

            print(f"[snapshot] 💾 fallback stored: {file_path} ({size} bytes)")

    # --------------------------------------------------
    # OPTIONAL READ
    # --------------------------------------------------

    def list_snapshots(self, device_uid: str) -> list:
        device_uid = self._safe_filename(device_uid)
        device_path = os.path.join(self.base_path, device_uid)

        if not os.path.exists(device_path):
            return []

        return [f for f in os.listdir(device_path) if f.endswith(".json")]

    def get_snapshot(self, snapshot_id: str, device_uid: str) -> Dict[str, Any]:
        device_uid = self._safe_filename(device_uid)

        file_path = os.path.join(
            self.base_path, device_uid, f"{snapshot_id}.json"
        )

        if not os.path.exists(file_path):
            return {}

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # --------------------------------------------------
    # 🔥 USER PREFERENCES FILTER
    # --------------------------------------------------

    def _apply_preferences(self, snapshot: Dict[str, Any], device_uid: str) -> Dict[str, Any]:
        pref_doc = get_preferences(device_uid) or {}
        prefs = pref_doc.get("preferences", {})

        defaults = {
            "include_state": True,
            "include_reason": True,
            "include_priority": True,
            "include_features": True,
            "include_temporal": True,
            "include_water": True,
            "include_battery": True,
            "include_touch": True,
            "include_decision": True,
            "include_context": True,
        }

        merged = {**defaults, **prefs}

        if not merged["include_state"]:
            snapshot.pop("state", None)

        if not merged["include_reason"]:
            snapshot.pop("reason", None)

        if not merged["include_priority"]:
            snapshot.pop("priority", None)

        if not merged["include_features"]:
            snapshot.pop("features", None)

        if not merged["include_temporal"]:
            snapshot.pop("temporal", None)

        if not merged["include_water"]:
            snapshot.pop("water", None)

        if not merged["include_decision"]:
            snapshot.pop("decision", None)

        if not merged["include_context"]:
            snapshot.pop("context", None)

        if "telemetry" in snapshot:
            telemetry = snapshot.get("telemetry") or {}

            if not merged["include_battery"]:
                telemetry.pop("battery", None)

            if not merged["include_touch"]:
                telemetry.pop("touch", None)

            snapshot["telemetry"] = telemetry

        snapshot["_meta"]["preferences_applied"] = merged

        return snapshot
