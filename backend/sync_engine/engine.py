# backend/sync_engine/engine.py

from backend.sync_engine.policy import SyncPolicy
from backend.utils.time import now_ms


class SyncEngine:
    def __init__(self, policy: SyncPolicy | None = None):
        self.policy = policy or SyncPolicy()
        self.last_sync_ms = 0
        self.last_emergency_ms = 0

        # NEW: prevents repeated snapshots while stable
        self._graceful_fired = False

    def decide(
        self,
        state: str,
        stable_duration_ms: int,
        emergency: dict | None = None,
    ) -> dict:
        """
        Decide whether to trigger a sync.

        - Emergency sync: physics-driven, overrides all gates
        - Graceful sync: ONE snapshot per stable episode
        """

        t = now_ms()

        # -------------------------------------------------
        # EMERGENCY OVERRIDE (DROP / WATER / IMPACT)
        # -------------------------------------------------
        if emergency:
            if t - self.last_emergency_ms < self.policy.emergency_cooldown_ms:
                return {
                    "sync": False,
                    "reason": "emergency_cooldown",
                    "type": "EMERGENCY",
                }

            self.last_emergency_ms = t
            self.last_sync_ms = t
            self._graceful_fired = False  # reset episode

            return {
                "sync": True,
                "reason": emergency.get("reason", "emergency_event"),
                "type": "EMERGENCY",
                "priority": "HIGH",
                "notify": True,
            }

        # -------------------------------------------------
        # GRACEFUL / STABILITY PATH
        # -------------------------------------------------

        # Motion or interaction resets stable episode
        if state in ("UNSTABLE", "MOVING", "USER_INTERACTION", "WATER_INTERACTION"):
            self._graceful_fired = False
            return {
                "sync": False,
                "reason": f"blocked_by_state:{state}",
                "type": "GRACEFUL",
            }

        # Require minimum stability proof
        if stable_duration_ms < self.policy.require_stable_ms:
            return {
                "sync": False,
                "reason": f"not_stable_long_enough:{stable_duration_ms}ms",
                "type": "GRACEFUL",
            }

        # Cooldown (still applies)
        if t - self.last_sync_ms < self.policy.cooldown_ms:
            return {
                "sync": False,
                "reason": "cooldown",
                "type": "GRACEFUL",
            }

        # Already snapped during this stable episode
        if self._graceful_fired:
            return {
                "sync": False,
                "reason": "already_synced_this_stable_episode",
                "type": "GRACEFUL",
            }
        

        # FIRE ONCE
        self.last_sync_ms = t
        self._graceful_fired = True

        return {
            "sync": True,
            "reason": "stable_window",
            "type": "GRACEFUL",
            "priority": "LOW",
            "notify": True,
        }