#!/usr/bin/env python3
"""
threshold_sweep.py — threshold sensitivity analysis for Autonomous Sync.

Replays detection logic over the raw logged feature stream at many
threshold settings. Needs no new data collection: every packet already
carries out.features (acc_norm, jerk, ...) as computed by the backend,
so we re-apply the decision rules from temporal_window.py rather than
re-running sensor fusion.

Answers, for each configuration:
  * how many free-fall and impact detections fire
  * how many free-fall -> impact pairs are physically plausible
  * how many pairs are single-tick artifacts (detected in adjacent
    frames, i.e. no actionable warning)
  * how many pairs give real pre-impact lead time
  * detections per hour on STILL/MOVING packets -- a false-positive proxy

Usage:
    python3 threshold_sweep.py ~/autosync_backup/devices -o ~/autosync_backup/rebuilt
"""

import argparse
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

G = 9.81
TICK_MS = 60                    # transmission interval
MAX_FALL_MS = 557.0             # 5 ft drop ceiling
ACTIONABLE_MS = 150.0           # below this there is no usable warning

# --- production defaults from backend/evaluator/temporal_window.py ---
DEFAULT_FF_ACC = 0.5
DEFAULT_FF_MIN_MS = 100
DEFAULT_IMPACT_JERK = 3.5


def load_packets(logdir):
    """Return {device_uid: structured array of (ts, acc_norm, jerk, state)}."""
    per_dev = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(logdir, "*.jsonl"))):
        print(f"  reading {os.path.basename(path)} ...", file=sys.stderr)
        with open(path, errors="ignore") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                pin = rec.get("in", {}) or {}
                pout = rec.get("out", {}) or {}
                ts = pin.get("ts")
                feats = pout.get("features") or {}
                acc = feats.get("acc_norm")
                jerk = feats.get("jerk")
                if ts is None or acc is None or jerk is None:
                    continue
                uid = pin.get("device_uid") or pout.get("device_uid") \
                    or pin.get("device_id") or "unknown"
                per_dev[uid].append((ts, float(acc), float(jerk),
                                     pout.get("state") or ""))
    out = {}
    for uid, rows in per_dev.items():
        rows.sort(key=lambda r: r[0])
        out[uid] = {
            "ts": np.array([r[0] for r in rows], dtype=np.float64),
            "acc": np.array([r[1] for r in rows], dtype=np.float64),
            "jerk": np.array([r[2] for r in rows], dtype=np.float64),
            "state": np.array([r[3] for r in rows], dtype=object),
        }
    return out


def detect(dev, ff_acc, ff_min_ms, impact_jerk, refractory_ms):
    """
    Re-apply detection rules to one device's packet stream.

    Free fall mirrors temporal_window.py: acc_norm <= ff_acc sustained
    for at least ff_min_ms. Impact is jerk >= impact_jerk, with an
    optional refractory period that collapses bursts from one physical
    event into a single detection.

    Returns (free_fall_ts, impact_ts) as arrays.
    """
    ts, acc, jerk = dev["ts"], dev["acc"], dev["jerk"]
    ff, imp = [], []

    ff_since = None
    ff_armed = False
    last_impact = -np.inf

    for i in range(len(ts)):
        t = ts[i]

        # ---- free fall: sustained low-g ----
        if acc[i] <= ff_acc:
            if ff_since is None:
                ff_since = t
                ff_armed = False
            if not ff_armed and (t - ff_since) >= ff_min_ms:
                ff.append(t)
                ff_armed = True
        else:
            ff_since = None
            ff_armed = False

        # ---- impact: jerk spike, with refractory ----
        if jerk[i] >= impact_jerk and (t - last_impact) >= refractory_ms:
            imp.append(t)
            last_impact = t

    return np.array(ff), np.array(imp)


def pair_leads(ff_ts, imp_ts, max_ms=MAX_FALL_MS):
    """Pair each free-fall with the next impact inside the physical window."""
    leads = []
    j = 0
    for t in ff_ts:
        while j < len(imp_ts) and imp_ts[j] < t:
            j += 1
        if j < len(imp_ts) and (imp_ts[j] - t) <= max_ms:
            leads.append(imp_ts[j] - t)
    return np.array(leads)


def benign_hours(devs):
    """Approximate streamed hours spent in STILL/MOVING (non-hazard) states."""
    total = 0.0
    for d in devs.values():
        n = int(np.sum((d["state"] == "STILL") | (d["state"] == "MOVING")))
        total += n * TICK_MS / 1000.0 / 3600.0
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logdir")
    ap.add_argument("-o", "--outdir", default="./rebuilt")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    devs = load_packets(args.logdir)
    n_pk = sum(len(d["ts"]) for d in devs.values())
    bh = benign_hours(devs)
    print(f"\nloaded {n_pk} packets across {len(devs)} devices "
          f"(~{bh:.1f} h in STILL/MOVING)\n")

    ff_grid = [0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15]
    sustain_grid = [100, 150, 200]
    jerk_grid = [3.5, 5.0, 7.0]
    refractory_grid = [0, 500, 1000]

    rows = []
    for ff_acc in ff_grid:
        for ff_min in sustain_grid:
            for jk in jerk_grid:
                for refr in refractory_grid:
                    n_ff = n_imp = 0
                    all_leads = []
                    for d in devs.values():
                        f, i = detect(d, ff_acc, ff_min, jk, refr)
                        n_ff += len(f)
                        n_imp += len(i)
                        all_leads.append(pair_leads(f, i))
                    leads = np.concatenate(all_leads) if all_leads else np.array([])
                    single_tick = int(np.sum(leads <= TICK_MS * 1.5))
                    actionable = leads[leads >= ACTIONABLE_MS]
                    rows.append({
                        "ff_acc_g": ff_acc,
                        "ff_sustain_ms": ff_min,
                        "impact_jerk": jk,
                        "refractory_ms": refr,
                        "n_free_fall": n_ff,
                        "n_impact": n_imp,
                        "n_pairs": len(leads),
                        "n_single_tick": single_tick,
                        "n_actionable": len(actionable),
                        "median_actionable_ms": (float(np.median(actionable))
                                                 if len(actionable) else np.nan),
                        "ff_per_benign_hour": n_ff / bh if bh else np.nan,
                        "impact_per_benign_hour": n_imp / bh if bh else np.nan,
                    })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(args.outdir, "threshold_sweep.csv"), index=False)

    pd.set_option("display.width", 220)

    print("=" * 78)
    print("FREE-FALL THRESHOLD SENSITIVITY")
    print("(production defaults elsewhere: sustain 100 ms, jerk 3.5, no refractory)")
    print("=" * 78)
    base = df[(df.ff_sustain_ms == DEFAULT_FF_MIN_MS) &
              (df.impact_jerk == DEFAULT_IMPACT_JERK) &
              (df.refractory_ms == 0)]
    print(base[["ff_acc_g", "n_free_fall", "n_pairs", "n_single_tick",
                "n_actionable", "median_actionable_ms",
                "ff_per_benign_hour"]].to_string(index=False))

    print("\n" + "=" * 78)
    print("SUSTAIN DURATION (at each free-fall level, jerk 3.5, no refractory)")
    print("=" * 78)
    s = df[(df.impact_jerk == DEFAULT_IMPACT_JERK) & (df.refractory_ms == 0)]
    print(s.pivot_table(index="ff_acc_g", columns="ff_sustain_ms",
                        values="n_actionable").to_string())

    print("\n" + "=" * 78)
    print("IMPACT REFRACTORY -- does it collapse detection bursts?")
    print("=" * 78)
    r = df[(df.ff_acc_g == DEFAULT_FF_ACC) &
           (df.ff_sustain_ms == DEFAULT_FF_MIN_MS)]
    print(r.pivot_table(index="impact_jerk", columns="refractory_ms",
                        values=["n_impact", "impact_per_benign_hour"]).to_string())

    print("\n" + "=" * 78)
    print("CONFIGS KEEPING ALL ACTIONABLE DETECTIONS AT LOWEST FALSE-POSITIVE RATE")
    print("=" * 78)
    best = df[df.n_actionable == df.n_actionable.max()] \
             .sort_values("ff_per_benign_hour")
    print(best.head(10).to_string(index=False))

    print(f"\nwrote {os.path.join(args.outdir, 'threshold_sweep.csv')}")


if __name__ == "__main__":
    main()
