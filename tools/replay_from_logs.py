import os, time
from backend.utils.jsonx import loads, dumps
from backend.api.runtime import Runtime

LOG_PATH = os.path.join("logs", "sensor_stream.jsonl")

def main():
    rt = Runtime()
    if not os.path.exists(LOG_PATH):
        print("No logs found.")
        return

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            rec = loads(line)
            pkt = rec["in"]

            acc = pkt.get("accel")
            gyr = pkt.get("gyro")
            if not acc or not gyr:
                continue

            import numpy as np
            acc_np = np.array([acc["x"], acc["y"], acc["z"]], dtype=float)
            gyr_np = np.array([gyr["x"], gyr["y"], gyr["z"]], dtype=float)

            feats = rt.fusion.step(pkt["ts"], acc_np, gyr_np)
            touch_active = bool(pkt.get("touch", {}).get("active", False))
            moisture_val = pkt.get("moisture", {}).get("value")

            state = rt.sm.classify(feats, touch_active, moisture_val).value
            decision = rt.sync.decide(state)

            out = {"state": state, "decision": decision, "features": feats}
            print(dumps(out))
            time.sleep(0.02)

if __name__ == "__main__":
    main()