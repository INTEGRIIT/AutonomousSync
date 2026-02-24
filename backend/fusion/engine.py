import numpy as np
from backend.fusion.filters import LowPass
from backend.fusion.orientation import ComplementaryOrientation
from backend.features.extractor import FeatureExtractor

class FusionEngine:
    def __init__(self):
        self.lp_acc = LowPass(alpha=0.85)
        self.lp_gyr = LowPass(alpha=0.85)
        self.orient = ComplementaryOrientation(alpha=0.98)
        self.fx = FeatureExtractor()

    def step(self, ts_ms: float, acc: np.ndarray, gyr: np.ndarray):
        acc_f = self.lp_acc.update(acc)
        gyr_f = self.lp_gyr.update(gyr)
        roll, pitch = self.orient.update(ts_ms, acc_f, gyr_f)
        feats = self.fx.compute(ts_ms, acc_f, gyr_f, roll, pitch)
        return feats