from backend.fusion.engine import FusionEngine
from backend.classifier.state_machine import StateMachine
from backend.sync_engine.engine import SyncEngine

from backend.evaluator.temporal_window import TemporalWindow
from backend.sensors.water_interaction import WaterInteractionSensor
from backend.evaluator.emergency_capture import EmergencyStateCapture
from backend.evaluator.state_transitions import StateTransitionEngine

class Runtime:
    def __init__(self):
        self.fusion = FusionEngine()
        self.temporal = TemporalWindow()
        self.water = WaterInteractionSensor()
        self.emergency = EmergencyStateCapture()

        self.sm = StateMachine()
        self.sync = SyncEngine()

        self.latest = None
        self.timeline = []   # last N outputs

        self.state_transition = StateTransitionEngine()

# =========================================================
# PER-DEVICE RUNTIME REGISTRY
#
# Runtime holds state that must not be shared: the low-pass filter
# memory, the previous acceleration sample used to compute jerk, the
# sliding temporal window, and the synchronization policy timers.
# A single global instance meant concurrent devices interleaved into
# one filter, so jerk could be computed as the difference between two
# different handsets.
#
# Instances are keyed by device_uid and evicted after an idle period,
# so a device reconnecting within that period keeps its window and
# filter continuity rather than starting cold.
# =========================================================

import time

_runtimes: dict[str, Runtime] = {}
_last_seen: dict[str, float] = {}

IDLE_EVICT_MS = 600_000   # 10 minutes


def get_runtime(device_uid: str) -> Runtime:
    now = time.time() * 1000.0
    stale = [u for u, t in _last_seen.items()
             if now - t > IDLE_EVICT_MS and u != device_uid]
    for u in stale:
        _runtimes.pop(u, None)
        _last_seen.pop(u, None)
    if device_uid not in _runtimes:
        _runtimes[device_uid] = Runtime()
    _last_seen[device_uid] = now
    return _runtimes[device_uid]


def drop_runtime(device_uid: str) -> None:
    _runtimes.pop(device_uid, None)
    _last_seen.pop(device_uid, None)


def active_runtimes() -> int:
    return len(_runtimes)


# Retained for the /latest and /timeline debug endpoints only. No
# detection path reads from this instance.
runtime = Runtime()