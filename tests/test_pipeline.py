from backend.api.runtime import Runtime
import numpy as np

def test_state_still():
    rt = Runtime()
    feats = rt.fusion.step(1000, np.array([0,0,9.81]), np.array([0,0,0]))
    st = rt.sm.classify(feats, touch_active=False, moisture=None).value
    assert st in ("STILL", "MOVING")  # depending on device units, still should dominate

def test_touch_interaction():
    rt = Runtime()
    feats = rt.fusion.step(1000, np.array([0,0,9.81]), np.array([0,0,0]))
    st = rt.sm.classify(feats, touch_active=True, moisture=None).value
    assert st == "USER_INTERACTION"