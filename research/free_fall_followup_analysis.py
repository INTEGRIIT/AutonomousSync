#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "free_fall_followup_analysis.xlsx"

# ==========================================================
# LOAD
# ==========================================================

df = pd.read_excel(INPUT_FILE)

# ==========================================================
# CLEAN
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

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

# ==========================================================
# SORT
# ==========================================================

df = (
    df
    .sort_values(
        [
            "device_name",
            "timestamp"
        ]
    )
    .reset_index(drop=True)
)

# ==========================================================
# NEXT EVENT
# ==========================================================

df["next_reason"] = (
    df.groupby("device_name")["reason"]
      .shift(-1)
)

df["next_timestamp"] = (
    df.groupby("device_name")["timestamp"]
      .shift(-1)
)

# ==========================================================
# FREE FALL EVENTS ONLY
# ==========================================================

free_falls = (
    df[
        df["reason"] == "free_fall"
    ]
    .copy()
)

free_falls["next_reason"] = (
    free_falls["next_reason"]
    .fillna("END")
)

# ==========================================================
# COUNTS
# ==========================================================

followup_counts = (
    free_falls["next_reason"]
    .value_counts()
    .reset_index()
)

followup_counts.columns = [
    "next_event",
    "count"
]

# ==========================================================
# PERCENTAGES
# ==========================================================

total_free_falls = len(
    free_falls
)

followup_counts["percent"] = (
    followup_counts["count"]
    / total_free_falls
    * 100
)

# ==========================================================
# TIMING
# ==========================================================

free_falls["delta_seconds"] = (
    free_falls["next_timestamp"]
    -
    free_falls["timestamp"]
).dt.total_seconds()

timing_summary = (
    free_falls
    .groupby("next_reason")
    ["delta_seconds"]
    .agg(
        [
            "count",
            "mean",
            "median",
            "min",
            "max"
        ]
    )
    .reset_index()
)

# ==========================================================
# DEVICE BREAKDOWN
# ==========================================================

device_followups = (
    free_falls
    .groupby(
        [
            "device_name",
            "next_reason"
        ]
    )
    .size()
    .reset_index(
        name="count"
    )
)

# ==========================================================
# EXPORT
# ==========================================================

with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="openpyxl"
) as writer:

    followup_counts.to_excel(
        writer,
        sheet_name="Followup Counts",
        index=False
    )

    timing_summary.to_excel(
        writer,
        sheet_name="Timing Summary",
        index=False
    )

    device_followups.to_excel(
        writer,
        sheet_name="Per Device",
        index=False
    )

    free_falls.to_excel(
        writer,
        sheet_name="Free Fall Events",
        index=False
    )

# ==========================================================
# PRINT
# ==========================================================

print()
print("========================================")
print("FREE FALL FOLLOW-UP ANALYSIS")
print("========================================")

print()

print(
    f"Total Free Fall Events: {total_free_falls}"
)

print()

print("NEXT EVENT AFTER FREE FALL")
print(
    followup_counts
)

print()

print("TIMING SUMMARY")
print(
    timing_summary
)

print()

print(
    f"Saved: {OUTPUT_FILE}"
)