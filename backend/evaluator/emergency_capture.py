from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from backend.utils.time import now_ms

@dataclass
class EmergencyConfig:
    capture_on_states: tuple = ("WATER_INTERACTION", "UNSTABLE")
    cooldown_ms: int = 3000

class EmergencyStateCapture:
    """
    Creates 'event snapshots' when critical states occur.
    These snapshots are what you sync to cloud / store for forensic replay.
    """
    def __init__(self, cfg: EmergencyConfig | None = None):
        self.cfg = cfg or EmergencyConfig()
        self._last_capture = 0

    def maybe_capture(self, state: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        t = now_ms()
        if state not in self.cfg.capture_on_states:
            return None
        if t - self._last_capture < self.cfg.cooldown_ms:
            return None
        self._last_capture = t
        return {
            "type": "EMERGENCY_SNAPSHOT",
            "ts": t,
            "state": state,
            "payload": payload,
        }