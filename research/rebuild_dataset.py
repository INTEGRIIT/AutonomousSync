#!/usr/bin/env python3
"""
rebuild_dataset.py — reconstruct the Autonomous Sync evaluation dataset
from raw per-device telemetry logs.

Replaces the hand-edited research/*.xlsx workbooks with a fully
regenerable pipeline. Every number the paper reports should come
out of this script.

Usage:
    python3 rebuild_dataset.py ~/autosync_backup/devices -o ./rebuilt

Key differences from the original analysis:
  * Device identity is device_uid, NOT device_name (names are a
    user-editable settings field and change mid-session).
  * Events are segmented into episodes by inter-event gap, so a burst
    of impact detections from one physical drop counts as one trial.
  * Lead-time pairing is constrained to within-episode free_fall ->
    impact with a physical maximum (a 5 ft drop is ~557 ms).
  * Reports the real FSM states (STILL/MOVING/UNSTABLE) separately
    from decision reasons (impact/free_fall/stable_window).
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

# --- physical constants -------------------------------------------------
G = 9.81
MAX_DROP_FT = 5.0
MAX_FALL_MS = (2 * (MAX_DROP_FT * 0.3048) / G) ** 0.5 * 1000  # ~557 ms

EVENT_REASONS = {"impact", "free_fall", "stable_window", "water"}


def iter_records(path):
    """Yield (in, out) dicts from a JSONL log, skipping malformed lines."""
    bad = 0
    with open(path, "r", errors="ignore") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                bad += 1
                continue
            yield rec.get("in", {}) or {}, rec.get("out", {}) or {}
    if bad:
        print(f"    (skipped {bad} malformed lines in {os.path.basename(path)})",
              file=sys.stderr)


def extract(paths):
    """Walk all logs; return (events_df, packets_df, name_map)."""
    events = []
    packet_stats = []
    names = defaultdict(Counter)

    for path in paths:
        print(f"  reading {os.path.basename(path)} ...", file=sys.stderr)
        for pin, pout in iter_records(path):
            ts = pin.get("ts")
            if ts is None:
                continue

            uid = pin.get("device_uid") or pout.get("device_uid") \
                or pin.get("device_id") or "unknown"
            name = pout.get("device_name")
            if name:
                names[uid][name] += 1

            # ---- packet-level metrics (Eq 1, 2, 3 partial) ----
            acc, gyr, mag = pin.get("accel"), pin.get("gyro"), pin.get("mag")
            skew_ag = skew_am = None
            if acc and gyr and acc.get("timestamp") and gyr.get("timestamp"):
                skew_ag = (acc["timestamp"] - gyr["timestamp"]) * 1000.0
            if acc and mag and acc.get("timestamp") and mag.get("timestamp"):
                skew_am = (acc["timestamp"] - mag["timestamp"]) * 1000.0
            proc_ms = None
            if pout.get("ts"):
                proc_ms = pout["ts"] * 1000.0 - ts
            # compact separators = true wire size, matching JS JSON.stringify
            wire_bytes = len(json.dumps(pin, separators=(",", ":")))

            packet_stats.append((uid, ts, pout.get("state"),
                                 skew_ag, skew_am, proc_ms, wire_bytes))

            # ---- event-level rows ----
            dec = pout.get("decision", {}) or {}
            reason = dec.get("reason")
            if reason in EVENT_REASONS or dec.get("type") == "EMERGENCY":
                feats = pout.get("features", {}) or {}
                temporal = pout.get("temporal", {}) or {}
                events.append({
                    "device_uid": uid,
                    "device_name": name,
                    "platform": pout.get("platform"),
                    "ts": ts,
                    "state": pout.get("state"),
                    "reason": reason,
                    "decision_type": dec.get("type"),
                    "sync": dec.get("sync"),
                    "acc_norm": feats.get("acc_norm"),
                    "gyr_norm": feats.get("gyr_norm"),
                    "jerk": feats.get("jerk"),
                    "stability": feats.get("stability"),
                    "stable_duration_ms": temporal.get("stable_duration_ms"),
                    "jerk_spike_rate": temporal.get("jerk_spike_rate"),
                    "source_file": os.path.basename(path),
                })

    ev = pd.DataFrame(events)
    pk = pd.DataFrame(packet_stats, columns=[
        "device_uid", "ts", "state", "skew_ag_ms", "skew_am_ms",
        "proc_ms", "wire_bytes"])
    return ev, pk, names


def segment_episodes(ev, gap_ms=2000):
    """Collapse event bursts into episodes: a gap > gap_ms starts a new one."""
    ev = ev.sort_values(["device_uid", "ts"]).reset_index(drop=True)
    ev["gap_ms"] = ev.groupby("device_uid")["ts"].diff()
    new = ev["gap_ms"].isna() | (ev["gap_ms"] > gap_ms)
    ev["episode_id"] = new.cumsum()
    return ev


def ceiling_for(height_ft):
    """
    Physical free-fall time for a given release height, in ms.

    Falls back to the 5 ft protocol maximum when the height is
    unknown. With custom heights now recordable per trial, a fixed
    ceiling would discard valid pairs from higher drops.
    """
    if not height_ft or height_ft <= 0:
        return MAX_FALL_MS
    return (2 * (float(height_ft) * 0.3048) / G) ** 0.5 * 1000


def lead_times(ev, max_ms=MAX_FALL_MS):
    """
    Within-episode free_fall -> impact pairing.

    Returns (all_pairs, physical_pairs). Pairs beyond max_ms are
    segmentation artifacts, not falls -- a 5 ft drop takes ~557 ms.
    """
    rows = []
    for eid, grp in ev.groupby("episode_id"):
        grp = grp.sort_values("ts")
        pending_ff = None
        for _, r in grp.iterrows():
            if r["reason"] == "free_fall":
                pending_ff = r
            elif r["reason"] == "impact" and pending_ff is not None:
                rows.append({
                    "episode_id": eid,
                    "device_uid": r["device_uid"],
                    "device_name": r["device_name"],
                    "height_ft": r.get("height_ft"),
                    "ff_ts": pending_ff["ts"],
                    "impact_ts": r["ts"],
                    "lead_time_ms": r["ts"] - pending_ff["ts"],
                })
                pending_ff = None
    allp = pd.DataFrame(rows)
    if allp.empty:
        return allp, allp
    # Per-trial ceiling where the trial recorded a height; the protocol
    # maximum otherwise.
    if "height_ft" in allp.columns:
        allp["ceiling_ms"] = allp["height_ft"].apply(ceiling_for)
    else:
        allp["ceiling_ms"] = MAX_FALL_MS
    phys = allp[allp["lead_time_ms"] <= allp["ceiling_ms"]].copy()
    phys["implied_height_ft"] = (
        0.5 * G * (phys["lead_time_ms"] / 1000.0) ** 2) / 0.3048
    return allp, phys


def describe(name, series):
    v = pd.to_numeric(series, errors="coerce").dropna().values
    if not len(v):
        return f"{name:24} (no data)"
    return (f"{name:24} n={len(v):7}  mean={v.mean():9.2f}  "
            f"p50={np.percentile(v,50):9.2f}  p95={np.percentile(v,95):9.2f}  "
            f"max={v.max():10.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logdir", help="directory of per-device .jsonl logs")
    ap.add_argument("-o", "--outdir", default="./rebuilt")
    ap.add_argument("--gap-ms", type=int, default=2000,
                    help="inter-event gap that starts a new episode")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.logdir, "*.jsonl")))
    if not paths:
        sys.exit(f"no .jsonl files under {args.logdir}")
    os.makedirs(args.outdir, exist_ok=True)

    ev, pk, names = extract(paths)
    if ev.empty:
        sys.exit("no events extracted -- check decision.reason values")

    ev = segment_episodes(ev, args.gap_ms)
    ev["dt"] = pd.to_datetime(ev["ts"], unit="ms")

    print("\n" + "=" * 72)
    print("DEVICE IDENTITY  (uid is stable; name is a user-editable setting)")
    print("=" * 72)
    for uid, ctr in sorted(names.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"{uid}  names={dict(ctr)}")

    print("\n" + "=" * 72)
    print("EVENTS BY DEVICE UID")
    print("=" * 72)
    tbl = ev.pivot_table(index="device_uid", columns="reason",
                         values="ts", aggfunc="count", fill_value=0)
    tbl["TOTAL"] = tbl.sum(axis=1)
    tbl["episodes"] = ev.groupby("device_uid")["episode_id"].nunique()
    print(tbl.to_string())
    print(f"\nTOTAL EVENTS: {len(ev)}   EPISODES: {ev['episode_id'].nunique()}"
          f"   ({len(ev)/max(1,ev['episode_id'].nunique()):.1f} events/episode)")
    print(f"EMERGENCY decisions: {(ev.decision_type=='EMERGENCY').sum()}")

    print("\n" + "=" * 72)
    print("FSM STATES  (packet level -- note MOVING, absent from the paper)")
    print("=" * 72)
    print(pk["state"].value_counts(dropna=False).to_string())

    print("\n" + "=" * 72)
    print("LEAD TIME: free_fall -> impact, within episode")
    print("=" * 72)
    allp, phys = lead_times(ev)
    print(f"all within-episode pairs: {len(allp)}")
    if len(allp):
        print(describe("  all pairs (ms)", allp["lead_time_ms"]))
    print(f"\nphysically plausible (<= {MAX_FALL_MS:.0f} ms, the 5 ft ceiling): "
          f"{len(phys)}")
    if len(phys):
        print(describe("  plausible (ms)", phys["lead_time_ms"]))
        print("\n" + phys[["device_name", "lead_time_ms",
                           "implied_height_ft"]].to_string(index=False))
    if len(allp) > len(phys):
        print(f"\n  {len(allp)-len(phys)} pairs exceed the physical ceiling and "
              f"are cross-trial artifacts, not falls.")

    print("\n" + "=" * 72)
    print("PACKET METRICS  (Eq 1 phase alignment, Eq 2 size, Eq 3 partial)")
    print("=" * 72)
    print(describe("accel-gyro skew (ms)", pk["skew_ag_ms"]))
    print(describe("accel-mag skew (ms)", pk["skew_am_ms"]))
    print(describe("backend proc (ms)", pk["proc_ms"]))
    print(describe("wire bytes", pk["wire_bytes"]))
    print("\nNOTE: proc_ms includes the per-packet TEMPORAL DEBUG print in "
          "temporal_window.py.\n      Remove it before quoting these as "
          "latency figures.")

    ev.to_csv(os.path.join(args.outdir, "events_rebuilt.csv"), index=False)
    allp.to_csv(os.path.join(args.outdir, "lead_times_all.csv"), index=False)
    phys.to_csv(os.path.join(args.outdir, "lead_times_physical.csv"), index=False)
    pk.sample(min(len(pk), 200000)).to_csv(
        os.path.join(args.outdir, "packet_metrics_sample.csv"), index=False)
    print(f"\nwrote outputs to {args.outdir}/")


if __name__ == "__main__":
    main()
