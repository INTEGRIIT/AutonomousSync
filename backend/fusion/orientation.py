import numpy as np
import math

class ComplementaryOrientation:
    """
    Complementary filter for roll/pitch using accel + gyro.
    Yaw from mag can be added later; for now we focus on stability + movement.
    """
    def __init__(self, alpha=0.98):
        self.alpha = alpha
        self.roll = 0.0
        self.pitch = 0.0
        self.last_ts = None

    def update(self, ts_ms: float, accel: np.ndarray, gyro: np.ndarray):
        # gyro in rad/s; accel in m/s^2-ish (Expo uses G; we’ll normalize in features)
        if self.last_ts is None:
            self.last_ts = ts_ms
            return self.roll, self.pitch

        dt = (ts_ms - self.last_ts) / 1000.0
        self.last_ts = ts_ms
        if dt <= 0 or dt > 1.0:
            dt = 0.02

        gx, gy, gz = gyro

        # integrate gyro
        roll_gyro = self.roll + gx * dt
        pitch_gyro = self.pitch + gy * dt

        ax, ay, az = accel
        # accel-derived roll/pitch
        roll_acc = math.atan2(ay, az)
        pitch_acc = math.atan2(-ax, math.sqrt(ay * ay + az * az))

        # complementary blend
        self.roll = self.alpha * roll_gyro + (1 - self.alpha) * roll_acc
        self.pitch = self.alpha * pitch_gyro + (1 - self.alpha) * pitch_acc

        return self.roll, self.pitch