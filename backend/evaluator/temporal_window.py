from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from typing import Deque, Dict, Any, Optional
import numpy as np


# =========================================================
# CONFIG (REAL-WORLD TUNED)
# =========================================================

@dataclass
class TemporalConfig:
    window_ms: int = 2500

    # Stability
    stable_epsilon: float = 9.5

    # Motion spike thresholds (REALISTIC)
    spike_jerk: float = 3.0
    spike_gyr: float = 0.8

    # Free fall (~0g)
    free_fall_acc_max: float = 0.5
    free_fall_min_ms: int = 100

    # Impact detection (REALISTIC)
    impact_jerk_min: float = 3.5
    impact_acc_min: float = 1.8

    # Tumbling / chaos motion
    tumbling_spike_rate: float = 0.4
    tumbling_motion_var: float = 0.2

    # Water detection
    water_emergency_level: float = 0.7


# =========================================================
# TEMPORAL ENGINE
# =========================================================

class TemporalWindow:
    """
    Elite Temporal Engine

    Responsibilities:
    - Stability detection
    - Motion pattern analysis
    - Emergency detection (physics-based)
    - AI-ready feature rollups
    """

    def __init__(self, cfg: TemporalConfig | None = None):
        self.cfg = cfg or TemporalConfig()
        self.buf: Deque[Dict[str, Any]] = deque()

        self._stable_since: Optional[float] = None
        self._free_fall_since: Optional[float] = None

    # -----------------------------------------------------
    # BUFFER MANAGEMENT
    # -----------------------------------------------------

    def _trim(self, now_ms: float):
        cutoff = now_ms - self.cfg.window_ms
        while self.buf and self.buf[0]["ts"] < cutoff:
            self.buf.popleft()

    # -----------------------------------------------------
    # MAIN UPDATE
    # -----------------------------------------------------

    def update(
        self,
        ts_ms: float,
        feats: Dict[str, float],
        touch_active: bool,
        moisture: Optional[float],
    ) -> Dict[str, Any]:

        # ---------------------------------
        # STORE SAMPLE
        # ---------------------------------

        self.buf.append({
            "ts": ts_ms,
            "feats": feats,
            "touch": touch_active,
            "moisture": moisture,
        })

        self._trim(ts_ms)

        # ---------------------------------
        # EXTRACT FEATURES (SAFE)
        # ---------------------------------

        stability = float(feats.get("stability", 999.0))
        acc_norm = float(feats.get("acc_norm", 9.8))
        jerk = float(feats.get("jerk", 0.0))
        gyr = float(feats.get("gyr_norm", 0.0))

        # ---------------------------------
        # STABILITY TRACKING
        # ---------------------------------

        if stability <= self.cfg.stable_epsilon and not touch_active:
            if self._stable_since is None:
                self._stable_since = ts_ms
        else:
            self._stable_since = None

        stable_duration_ms = int(ts_ms - self._stable_since) if self._stable_since else 0

        # ---------------------------------
        # FREE FALL DETECTION
        # ---------------------------------

        if acc_norm <= self.cfg.free_fall_acc_max:
            if self._free_fall_since is None:
                self._free_fall_since = ts_ms
        else:
            self._free_fall_since = None

        free_fall_detected = (
            self._free_fall_since is not None
            and (ts_ms - self._free_fall_since) >= self.cfg.free_fall_min_ms
        )

        # ---------------------------------
        # ROLLUP ARRAYS
        # ---------------------------------

        stabs = np.array([x["feats"].get("stability", 999.0) for x in self.buf], dtype=float)
        jerks = np.array([x["feats"].get("jerk", 0.0) for x in self.buf], dtype=float)
        gyrs  = np.array([x["feats"].get("gyr_norm", 0.0) for x in self.buf], dtype=float)

        # ---------------------------------
        # STATISTICS
        # ---------------------------------

        touch_ratio = float(sum(1 for x in self.buf if x["touch"]) / max(1, len(self.buf)))

        jerk_spike_rate = float(np.mean(jerks > self.cfg.spike_jerk))
        gyr_spike_rate  = float(np.mean(gyrs  > self.cfg.spike_gyr))

        motion_variance = float(np.var(gyrs) + np.var(jerks))

        moisture_vals = [x["moisture"] for x in self.buf if x["moisture"] is not None]
        moisture_mean = float(np.mean(moisture_vals)) if moisture_vals else None

        # ---------------------------------
        # 🚨 EMERGENCY DETECTION (IMPROVED)
        # ---------------------------------

        # 🔥 IMPACT (pattern-based + instant spike)
        impact_detected = (
            jerk >= self.cfg.impact_jerk_min
            or jerk_spike_rate > 0.3
        )

        # 🔥 TUMBLING (chaotic motion)
        tumbling_detected = (
            gyr_spike_rate >= self.cfg.tumbling_spike_rate
            and motion_variance >= self.cfg.tumbling_motion_var
        )

        # 🔥 WATER
        water_emergency = (
            moisture_mean is not None
            and moisture_mean >= self.cfg.water_emergency_level
        )

        # ---------------------------------
        # DEBUG (CRITICAL FOR YOU RIGHT NOW)
        # ---------------------------------

        print("🧠 TEMPORAL DEBUG:", {
            "acc_norm": round(acc_norm, 3),
            "jerk": round(jerk, 3),
            "gyr": round(gyr, 3),
            "impact": impact_detected,
            "free_fall": free_fall_detected,
            "tumbling": tumbling_detected,
        })

        # ---------------------------------
        # OUTPUT
        # ---------------------------------

        return {
            "window_ms": self.cfg.window_ms,
            "stable_duration_ms": stable_duration_ms,

            "stability_mean": float(np.mean(stabs)) if len(stabs) else 0.0,
            "stability_std": float(np.std(stabs)) if len(stabs) else 0.0,

            "touch_ratio": touch_ratio,
            "jerk_spike_rate": jerk_spike_rate,
            "gyr_spike_rate": gyr_spike_rate,
            "motion_variance": motion_variance,

            "moisture_mean": moisture_mean,
            "samples": len(self.buf),

            # 🚨 FINAL FLAGS
            "free_fall": free_fall_detected,
            "impact": impact_detected,
            "tumbling": tumbling_detected,
            "water_emergency": water_emergency,
        }
