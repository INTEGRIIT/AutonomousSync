# backend/sync_engine/engine.py

from backend.sync_engine.policy import SyncPolicy
from backend.utils.time import now_ms


class SyncEngine:
    def __init__(self, policy: SyncPolicy | None = None):
        self.policy = policy or SyncPolicy()
        self.last_sync_ms = 0
        self.last_emergency_ms = 0

        # Prevent repeated graceful triggers
        self._graceful_fired = False

    def decide(
        self,
        state: str,
        stable_duration_ms: int,
        emergency: dict | None = None,
    ) -> dict:

        t = now_ms()

        # =================================================
        # 🔥 DEBUG VISIBILITY (CRITICAL)
        # =================================================
        print("🧠 ENGINE INPUT:", {
            "state": state,
            "stable_duration_ms": stable_duration_ms,
            "emergency": emergency,
        })

        # =================================================
        # 🚨 EMERGENCY PATH (PRIORITY SYSTEM)
        # =================================================
        if emergency:

            print("🚨 EMERGENCY DETECTED:", emergency)

            # 🔥 TEMP: DISABLE COOLDOWN FOR TESTING
            # Comment this back later for production
            """
            if t - self.last_emergency_ms < self.policy.emergency_cooldown_ms:
                print("⛔ BLOCKED: emergency cooldown")
                return {
                    "sync": False,
                    "reason": "emergency_cooldown",
                    "type": "EMERGENCY",
                }
            """

            print("🔥 EMERGENCY SYNC TRIGGERED")

            self.last_emergency_ms = t
            self.last_sync_ms = t
            self._graceful_fired = False

            return {
                "sync": True,
                "reason": emergency.get("reason", "emergency_event"),
                "type": "EMERGENCY",
                "priority": "HIGH",
                "notify": True,
            }

        # =================================================
        # 🧘 GRACEFUL PATH
        # =================================================

        if state in ("UNSTABLE", "MOVING", "USER_INTERACTION", "WATER_INTERACTION"):
            print("⛔ BLOCKED: unstable state", state)
            self._graceful_fired = False
            return {
                "sync": False,
                "reason": f"blocked_by_state:{state}",
                "type": "GRACEFUL",
            }

        if stable_duration_ms < self.policy.require_stable_ms:
            print("⛔ BLOCKED: not stable long enough", stable_duration_ms)
            return {
                "sync": False,
                "reason": f"not_stable_long_enough:{stable_duration_ms}ms",
                "type": "GRACEFUL",
            }

        if t - self.last_sync_ms < self.policy.cooldown_ms:
            print("⛔ BLOCKED: cooldown")
            return {
                "sync": False,
                "reason": "cooldown",
                "type": "GRACEFUL",
            }

        if self._graceful_fired:
            print("⛔ BLOCKED: already fired")
            return {
                "sync": False,
                "reason": "already_synced_this_stable_episode",
                "type": "GRACEFUL",
            }

        # =================================================
        # ✅ FIRE GRACEFUL
        # =================================================
        print("✅ GRACEFUL SYNC TRIGGERED")

        self.last_sync_ms = t
        self._graceful_fired = True

        return {
            "sync": True,
            "reason": "stable_window",
            "type": "GRACEFUL",
            "priority": "LOW",
            "notify": True,
        }