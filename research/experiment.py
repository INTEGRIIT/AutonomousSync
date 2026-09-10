#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "autonomous_sync_analysis.xlsx"

# ==========================================================
# LOAD
# ==========================================================

df = pd.read_excel(INPUT_FILE)

# ==========================================================
# CLEANUP
# ==========================================================

df["reason"] = (
    df["reason"]
    .astype(str)
    .str.strip()
    .str.lower()
)

df["device_name"] = (
    df["device_name"]
    .astype(str)
    .str.strip()
)

# ==========================================================
# DATASET OVERVIEW
# ==========================================================

total_devices = (
    df["device_name"]
    .nunique()
)

total_runs = len(
    df[
        ["device_name", "run_number"]
    ]
    .drop_duplicates()
)

total_events = len(df)

# ==========================================================
# EVENT DISTRIBUTION
# ==========================================================

impact_count = (
    df["reason"]
    .eq("impact")
    .sum()
)

free_fall_count = (
    df["reason"]
    .eq("free_fall")
    .sum()
)

stable_count = (
    df["reason"]
    .eq("stable_window")
    .sum()
)

# ==========================================================
# PUSH SUCCESS
# ==========================================================

push_attempts = (
    df["push_attempted"]
    .fillna(0)
    .astype(int)
    .sum()
)

push_success = (
    df["push_success"]
    .fillna(0)
    .astype(int)
    .sum()
)

push_success_rate = (
    push_success / push_attempts
    if push_attempts > 0
    else 0
)

# ==========================================================
# SYNC SUCCESS
# ==========================================================

sync_triggered = (
    df["sync_triggered"]
    .fillna(0)
    .astype(int)
    .sum()
)

sync_rate = (
    sync_triggered / total_events
    if total_events > 0
    else 0
)

# ==========================================================
# EVENTS PER RUN
# ==========================================================

events_per_run = (
    df.groupby(
        [
            "device_name",
            "run_number"
        ]
    )
    .size()
)

events_per_run_summary = pd.DataFrame(
    [
        [
            events_per_run.min(),
            events_per_run.mean(),
            events_per_run.max()
        ]
    ],
    columns=[
        "min_events_per_run",
        "avg_events_per_run",
        "max_events_per_run"
    ]
)

# ==========================================================
# PER DEVICE RESULTS
# ==========================================================

device_summary = []

for device in sorted(
    df["device_name"]
    .dropna()
    .unique()
):

    subset = df[
        df["device_name"] == device
    ]

    runs = (
        subset["run_number"]
        .nunique()
    )

    events = len(subset)

    impacts = (
        subset["reason"]
        .eq("impact")
        .sum()
    )

    free_falls = (
        subset["reason"]
        .eq("free_fall")
        .sum()
    )

    stable = (
        subset["reason"]
        .eq("stable_window")
        .sum()
    )

    device_summary.append(
        [
            device,
            runs,
            events,
            impacts,
            free_falls,
            stable
        ]
    )

device_summary = pd.DataFrame(
    device_summary,
    columns=[
        "device_name",
        "runs",
        "events",
        "impact_events",
        "free_fall_events",
        "stable_events"
    ]
)

# ==========================================================
# OVERALL SUMMARY
# ==========================================================

summary = pd.DataFrame(
    [
        ["Devices", total_devices],
        ["Runs", total_runs],
        ["Events", total_events],
        ["Impact Events", impact_count],
        ["Free Fall Events", free_fall_count],
        ["Stable Events", stable_count],
        ["Push Attempts", push_attempts],
        ["Push Successes", push_success],
        ["Push Success Rate", push_success_rate],
        ["Sync Triggered", sync_triggered],
        ["Sync Rate", sync_rate],
    ],
    columns=[
        "Metric",
        "Value"
    ]
)

# ==========================================================
# EXPORT
# ==========================================================

with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="openpyxl"
) as writer:

    summary.to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

    device_summary.to_excel(
        writer,
        sheet_name="Per Device",
        index=False
    )

    events_per_run_summary.to_excel(
        writer,
        sheet_name="Events Per Run",
        index=False
    )

    df.to_excel(
        writer,
        sheet_name="Raw Data",
        index=False
    )

# ==========================================================
# CONSOLE OUTPUT
# ==========================================================

print("\n==============================")
print("AUTONOMOUS SYNC ANALYSIS")
print("==============================")

print(f"Devices       : {total_devices}")
print(f"Runs          : {total_runs}")
print(f"Events        : {total_events}")

print(f"\nImpact Events : {impact_count}")
print(f"Free Falls    : {free_fall_count}")
print(f"Stable Events : {stable_count}")

print(f"\nPush Success Rate : {push_success_rate:.2%}")
print(f"Sync Rate         : {sync_rate:.2%}")

print("\nPer Device")
print(device_summary)

print("\nEvents Per Run")
print(events_per_run_summary)

print(f"\nSaved: {OUTPUT_FILE}")