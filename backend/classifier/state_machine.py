from backend.classifier.states import SystemState

class StateMachine:
    """
    Diamond-tier classifier:
    - Base motion + stability
    - Temporal context overrides
    - WaterInteractionSensor signal overrides
    """
    def classify(self, feats: dict, temporal: dict, water: dict, touch_active: bool):
        stability = float(feats["stability"])
        acc_norm = float(feats["acc_norm"])
        gyr_norm = float(feats["gyr_norm"])
        jerk = float(feats["jerk"])

        stable_ms = int(temporal.get("stable_duration_ms", 0))

        # Highest priority: water interaction
        if water.get("is_water", False):
            return SystemState.WATER_INTERACTION

        # Next: explicit user interaction (but not water)
        if touch_active:
            return SystemState.USER_INTERACTION

        # Unstable: sustained instability or spikes
        if stability > 12.0 or jerk > 14.0:
            return SystemState.UNSTABLE

        # STILL has priority once proven over time
        if stable_ms >= 800:
            return SystemState.STILL

        # Moving (only if not yet proven still)
        if abs(acc_norm - 9.81) > 1.2 or gyr_norm > 1.2:
            return SystemState.MOVING

        # Default conservative
        return SystemState.MOVING