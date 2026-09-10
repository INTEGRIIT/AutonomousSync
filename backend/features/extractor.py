import numpy as np
from backend.sensors.sanity import norm3

class FeatureExtractor:
    def __init__(self):
        self.prev_acc = None
        self.prev_ts = None

    def compute(self, ts_ms: float, acc: np.ndarray, gyr: np.ndarray, roll: float, pitch: float):
        acc_norm = norm3(acc)
        gyr_norm = norm3(gyr)

        # jerk (derivative of accel magnitude)
        jerk = 0.0
        if self.prev_acc is not None and self.prev_ts is not None:
            dt = (ts_ms - self.prev_ts) / 1000.0
            if dt > 0:
                jerk = float((norm3(acc) - norm3(self.prev_acc)) / dt)

        self.prev_acc = acc
        self.prev_ts = ts_ms

        # “stability score” (lower is more stable)
        # acc_norm is in G (Expo sensors), not m/s^2
        stability = float(abs(acc_norm - 1.0) + gyr_norm)

        return {
            "acc_norm": float(acc_norm),
            "gyr_norm": float(gyr_norm),
            "jerk": float(jerk),
            "roll": float(roll),
            "pitch": float(pitch),
            "stability": float(stability),
        }