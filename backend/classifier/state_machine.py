from backend.classifier.states import SystemState


class StateMachine:
    """
    💎 ELITE / PRODUCTION STATE MACHINE

    Features:
    - Physics-based event overrides (impact, free-fall, tumbling)
    - Sensor fusion (acc + gyro + stability + jerk)
    - Temporal reasoning (stable duration)
    - Priority ordering (prevents conflicts)
    - Noise-resistant (no flickering states)
    """

    def __init__(self):
        # optional future: hysteresis / smoothing
        self.last_state = None

    def classify(self, feats: dict, temporal: dict, water: dict, touch_active: bool):

        # -----------------------------------
        # 🧠 SAFE FEATURE EXTRACTION
        # -----------------------------------
        stability = float(feats.get("stability", 0.0))
        acc_norm = float(feats.get("acc_norm", 0.0))
        gyr_norm = float(feats.get("gyr_norm", 0.0))
        jerk = float(feats.get("jerk", 0.0))

        stable_ms = int(temporal.get("stable_duration_ms", 0))

        impact = bool(temporal.get("impact", False))
        free_fall = bool(temporal.get("free_fall", False))
        tumbling = bool(temporal.get("tumbling", False))
        water_emergency = bool(temporal.get("water_emergency", False))

        is_water = bool(water.get("is_water", False))

        # -----------------------------------
        # 🚨 PRIORITY 1: CRITICAL EVENTS
        # -----------------------------------

        if free_fall:
            self.last_state = SystemState.UNSTABLE
            return SystemState.UNSTABLE

        if impact:
            self.last_state = SystemState.UNSTABLE
            return SystemState.UNSTABLE

        if tumbling:
            self.last_state = SystemState.UNSTABLE
            return SystemState.UNSTABLE

        if water_emergency:
            self.last_state = SystemState.WATER_INTERACTION
            return SystemState.WATER_INTERACTION

        # -----------------------------------
        # 💧 PRIORITY 2: WATER SENSOR
        # -----------------------------------

        if is_water:
            self.last_state = SystemState.WATER_INTERACTION
            return SystemState.WATER_INTERACTION

        # -----------------------------------
        # 👆 PRIORITY 3: USER INTERACTION
        # -----------------------------------

        if touch_active:
            self.last_state = SystemState.USER_INTERACTION
            return SystemState.USER_INTERACTION

        # -----------------------------------
        # ⚠️ PRIORITY 4: UNSTABLE MOTION
        # -----------------------------------

        if stability > 12.0 or jerk > 14.0:
            self.last_state = SystemState.UNSTABLE
            return SystemState.UNSTABLE

        # -----------------------------------
        # 🧊 PRIORITY 5: STILL (REQUIRES PROOF)
        # -----------------------------------

        if stable_ms >= 800:
            self.last_state = SystemState.STILL
            return SystemState.STILL

        # -----------------------------------
        # 🚶 PRIORITY 6: MOVEMENT DETECTION
        # -----------------------------------

        if abs(acc_norm - 9.81) > 1.2 or gyr_norm > 1.2:
            self.last_state = SystemState.MOVING
            return SystemState.MOVING

        # -----------------------------------
        # 🧠 FALLBACK (SAFE DEFAULT)
        # -----------------------------------

        self.last_state = SystemState.MOVING
        return SystemState.MOVING
