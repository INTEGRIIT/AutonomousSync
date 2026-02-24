from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from typing import Deque, Dict, Any, Optional
import numpy as np


@dataclass
class TemporalConfig:
    window_ms: int = 2500

    # Stability
    stable_epsilon: float = 9.5

    # Emergency thresholds
    spike_jerk: float = 10.0
    spike_gyr: float = 1.2

    free_fall_acc_max: float = 0.3      # ~0g
    free_fall_min_ms: int = 120

    impact_jerk_min: float = 12.0
    impact_acc_min: float = 2.5

    tumbling_spike_rate: float = 0.6
    tumbling_motion_var: float = 0.5

    water_emergency_level: float = 0.7


class TemporalWindow:
    """
    Holds rolling feature history for temporal inference.
    Provides:
      - stability metrics
      - motion statistics
      - emergency event detection (physics-based)
    """

    def __init__(self, cfg: TemporalConfig | None = None):
        self.cfg = cfg or TemporalConfig()
        self.buf: Deque[Dict[str, Any]] = deque()
        self._stable_since: Optional[float] = None
        self._free_fall_since: Optional[float] = None

    def _trim(self, now_ms: float):
        cutoff = now_ms - self.cfg.window_ms
        while self.buf and self.buf[0]["ts"] < cutoff:
            self.buf.popleft()

    def update(
        self,
        ts_ms: float,
        feats: Dict[str, float],
        touch_active: bool,
        moisture: Optional[float],
    ) -> Dict[str, Any]:

        self.buf.append({
            "ts": ts_ms,
            "feats": feats,
            "touch": touch_active,
            "moisture": moisture,
        })
        self._trim(ts_ms)

        stability = float(feats.get("stability", 999.0))
        acc_norm = float(feats.get("acc_norm", 9.8))
        jerk = float(feats.get("jerk", 0.0))
        gyr = float(feats.get("gyr_norm", 0.0))

        # -----------------------------
        # Stable duration tracking
        # -----------------------------
        if stability <= self.cfg.stable_epsilon and not touch_active:
            if self._stable_since is None:
                self._stable_since = ts_ms
        else:
            self._stable_since = None

        stable_duration_ms = int(ts_ms - self._stable_since) if self._stable_since else 0

        # -----------------------------
        # Free-fall detection
        # -----------------------------
        if acc_norm <= self.cfg.free_fall_acc_max:
            if self._free_fall_since is None:
                self._free_fall_since = ts_ms
        else:
            self._free_fall_since = None

        free_fall_detected = (
            self._free_fall_since is not None
            and (ts_ms - self._free_fall_since) >= self.cfg.free_fall_min_ms
        )

        # -----------------------------
        # Rollups
        # -----------------------------
        stabs = np.array([x["feats"].get("stability", 999.0) for x in self.buf], dtype=float)
        jerks = np.array([x["feats"].get("jerk", 0.0) for x in self.buf], dtype=float)
        gyrs  = np.array([x["feats"].get("gyr_norm", 0.0) for x in self.buf], dtype=float)

        touch_ratio = float(sum(1 for x in self.buf if x["touch"]) / max(1, len(self.buf)))

        jerk_spike_rate = float(np.mean(jerks > self.cfg.spike_jerk))
        gyr_spike_rate  = float(np.mean(gyrs  > self.cfg.spike_gyr))

        motion_variance = float(np.var(gyrs) + np.var(jerks))

        moisture_vals = [x["moisture"] for x in self.buf if x["moisture"] is not None]
        moisture_mean = float(np.mean(moisture_vals)) if moisture_vals else None

        # -----------------------------
        # Emergency events
        # -----------------------------
        impact_detected = (
            jerk >= self.cfg.impact_jerk_min
            and acc_norm >= self.cfg.impact_acc_min
        )

        tumbling_detected = (
            gyr_spike_rate >= self.cfg.tumbling_spike_rate
            and motion_variance >= self.cfg.tumbling_motion_var
        )

        water_emergency = (
            moisture_mean is not None
            and moisture_mean >= self.cfg.water_emergency_level
        )

        return {
            "window_ms": self.cfg.window_ms,
            "stable_duration_ms": stable_duration_ms,
            "stability_mean": float(np.mean(stabs)),
            "stability_std": float(np.std(stabs)),
            "touch_ratio": touch_ratio,
            "jerk_spike_rate": jerk_spike_rate,
            "gyr_spike_rate": gyr_spike_rate,
            "motion_variance": motion_variance,
            "moisture_mean": moisture_mean,
            "samples": len(self.buf),

            # 🔴 Emergency flags
            "free_fall": free_fall_detected,
            "impact": impact_detected,
            "tumbling": tumbling_detected,
            "water_emergency": water_emergency,
        }