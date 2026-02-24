from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class WaterConfig:
    # Tunable weights for confidence scoring
    w_touch: float = 0.35
    w_spikes: float = 0.35
    w_moisture: float = 0.30

    # Decision thresholds
    confidence_threshold: float = 0.70

class WaterInteractionSensor:
    """
    Infers 'water interaction' from temporal context:
      - sustained touch (touch_ratio)
      - instability spikes (jerk_spike_rate, gyr_spike_rate)
      - moisture hint (moisture_mean) if present (BLE later)
    Outputs:
      - is_water: bool
      - confidence: float 0..1
      - rationale: str (debug/proof)
    """
    def __init__(self, cfg: WaterConfig | None = None):
        self.cfg = cfg or WaterConfig()

    def infer(self, temporal: Dict[str, Any]) -> Dict[str, Any]:
        touch_ratio = float(temporal.get("touch_ratio", 0.0))
        jerk_rate = float(temporal.get("jerk_spike_rate", 0.0))
        gyr_rate  = float(temporal.get("gyr_spike_rate", 0.0))
        spikes = max(jerk_rate, gyr_rate)

        moisture_mean: Optional[float] = temporal.get("moisture_mean", None)
        moisture_score = 0.0
        if moisture_mean is not None:
            # assume moisture already normalized 0..1
            moisture_score = max(0.0, min(1.0, float(moisture_mean)))

        # Confidence scoring (bounded)
        conf = (
            self.cfg.w_touch * min(1.0, touch_ratio / 0.75) +      # saturate around 75% touch
            self.cfg.w_spikes * min(1.0, spikes / 0.60) +          # spikes saturate around 60% rate
            self.cfg.w_moisture * moisture_score
        )
        conf = max(0.0, min(1.0, conf))

        is_water = conf >= self.cfg.confidence_threshold

        rationale = f"touch={touch_ratio:.2f}, spikes={spikes:.2f}, moisture={moisture_score:.2f}, conf={conf:.2f}"
        return {"is_water": is_water, "confidence": conf, "rationale": rationale}