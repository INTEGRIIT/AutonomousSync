#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "stable_duration_analysis.xlsx"

# ==========================================================
# CONFIG
# ==========================================================

OUTLIER_THRESHOLD_MS = 60000  # 60 seconds

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

# ==========================================================
# STABLE EVENTS ONLY
# ==========================================================

stable_df = df[
    df["reason"] == "stable_window"
].copy()

stable_df = stable_df[
    stable_df["temporal_stable_duration_ms"] > 0
]

# ==========================================================
# FILTERED VERSION
# ==========================================================

filtered_df = stable_df[
    stable_df["temporal_stable_duration_ms"]
    <= OUTLIER_THRESHOLD_MS
].copy()

# ==========================================================
# RAW STATS
# ==========================================================

raw_count = len(stable_df)

raw_mean = stable_df["temporal_stable_duration_ms"].mean()
raw_median = stable_df["temporal_stable_duration_ms"].median()
raw_min = stable_df["temporal_stable_duration_ms"].min()
raw_max = stable_df["temporal_stable_duration_ms"].max()
raw_std = stable_df["temporal_stable_duration_ms"].std()

# ==========================================================
# FILTERED STATS
# ==========================================================

filtered_count = len(filtered_df)

filtered_mean = filtered_df["temporal_stable_duration_ms"].mean()
filtered_median = filtered_df["temporal_stable_duration_ms"].median()
filtered_min = filtered_df["temporal_stable_duration_ms"].min()
filtered_max = filtered_df["temporal_stable_duration_ms"].max()
filtered_std = filtered_df["temporal_stable_duration_ms"].std()

# ==========================================================
# PERCENTILES (FILTERED)
# ==========================================================

p25 = filtered_df["temporal_stable_duration_ms"].quantile(0.25)
p75 = filtered_df["temporal_stable_duration_ms"].quantile(0.75)
p90 = filtered_df["temporal_stable_duration_ms"].quantile(0.90)
p95 = filtered_df["temporal_stable_duration_ms"].quantile(0.95)

# ==========================================================
# PER DEVICE (FILTERED)
# ==========================================================

device_summary = (
    filtered_df
    .groupby("device_name")
    ["temporal_stable_duration_ms"]
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
# SUMMARY
# ==========================================================

summary = pd.DataFrame(
    [
        ["Raw Stable Events", raw_count],
        ["Raw Mean (ms)", raw_mean],
        ["Raw Median (ms)", raw_median],
        ["Raw Min (ms)", raw_min],
        ["Raw Max (ms)", raw_max],
        ["Raw Std Dev (ms)", raw_std],

        ["Filtered Stable Events", filtered_count],
        ["Filtered Mean (ms)", filtered_mean],
        ["Filtered Median (ms)", filtered_median],
        ["Filtered Min (ms)", filtered_min],
        ["Filtered Max (ms)", filtered_max],
        ["Filtered Std Dev (ms)", filtered_std],

        ["25th Percentile", p25],
        ["75th Percentile", p75],
        ["90th Percentile", p90],
        ["95th Percentile", p95],
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

    stable_df.to_excel(
        writer,
        sheet_name="Raw Stable Events",
        index=False
    )

    filtered_df.to_excel(
        writer,
        sheet_name="Filtered Stable Events",
        index=False
    )

# ==========================================================
# PRINT RESULTS
# ==========================================================

print()
print("========================================")
print("STABLE DURATION ANALYSIS")
print("========================================")

print()
print("RAW DATA")
print(f"Count  : {raw_count}")
print(f"Mean   : {raw_mean:,.2f} ms")
print(f"Median : {raw_median:,.2f} ms")
print(f"Max    : {raw_max:,.2f} ms")

print()
print("FILTERED (< 60 sec)")
print(f"Count  : {filtered_count}")
print(f"Mean   : {filtered_mean:,.2f} ms")
print(f"Median : {filtered_median:,.2f} ms")
print(f"Max    : {filtered_max:,.2f} ms")

print()
print(device_summary)

print()
print(f"Saved: {OUTPUT_FILE}")