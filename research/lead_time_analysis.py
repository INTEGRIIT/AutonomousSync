#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "lead_time_analysis.xlsx"

# ==========================================================
# CONFIG
# ==========================================================

MAX_EPISODE_GAP_SECONDS = 10

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
    df["timestamp"]
)

# ==========================================================
# DEVICES FOUND
# ==========================================================

print("\nDevices Found:\n")

print(
    f"\nUnique Devices: "
    f"{df['device_name'].nunique()}"
)

for device in sorted(
    df["device_name"].unique()
):
    print(repr(device))

# ==========================================================
# SORT
# ==========================================================

df = df.sort_values(
    [
        "device_name",
        "timestamp"
    ]
)

print(
    "\nRows Per Device:\n"
)

print(
    df["device_name"]
    .value_counts()
)

# ==========================================================
# FIND FREEFALL -> IMPACT CHAINS
# ==========================================================

lead_times = []

for device in df["device_name"].unique():

    device_df = (
        df[
            df["device_name"] == device
        ]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    free_fall_time = None

    for _, row in device_df.iterrows():

        reason = row["reason"]
        ts = row["timestamp"]

        # remember latest free-fall

        # remember FIRST free-fall in chain

        if (
            reason == "free_fall"
            and free_fall_time is None
        ):
            free_fall_time = ts

        # impact after free-fall

        elif (
            reason == "impact"
            and free_fall_time is not None
        ):

            lead_ms = (
                ts - free_fall_time
            ).total_seconds() * 1000

            if (
                lead_ms > 0
                and lead_ms <=
                MAX_EPISODE_GAP_SECONDS * 1000
            ):

                lead_times.append(
                    [
                        device,
                        free_fall_time,
                        ts,
                        lead_ms
                    ]
                )

            free_fall_time = None

# ==========================================================
# RESULTS TABLE
# ==========================================================

lead_df = pd.DataFrame(
    lead_times,
    columns=[
        "device_name",
        "free_fall_timestamp",
        "impact_timestamp",
        "lead_time_ms"
    ]
)

# ==========================================================
# SUMMARY
# ==========================================================

if len(lead_df):

    summary = pd.DataFrame(
        [
            [
                len(lead_df),
                lead_df["lead_time_ms"].mean(),
                lead_df["lead_time_ms"].median(),
                lead_df["lead_time_ms"].min(),
                lead_df["lead_time_ms"].max(),
                lead_df["lead_time_ms"].std()
            ]
        ],
        columns=[
            "episodes",
            "mean_ms",
            "median_ms",
            "min_ms",
            "max_ms",
            "std_ms"
        ]
    )

else:

    summary = pd.DataFrame(
        [
            [0,0,0,0,0,0]
        ],
        columns=[
            "episodes",
            "mean_ms",
            "median_ms",
            "min_ms",
            "max_ms",
            "std_ms"
        ]
    )

# ==========================================================
# PER DEVICE
# ==========================================================

device_summary = (
    lead_df
    .groupby("device_name")
    ["lead_time_ms"]
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

print("\nLead Times (ms):\n")

print(
    lead_df["lead_time_ms"]
    .sort_values()
    .tolist()
)

# ==========================================================
# EXPORT
# ==========================================================

with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="openpyxl"
) as writer:

    lead_df.to_excel(
        writer,
        sheet_name="Lead Times",
        index=False
    )

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

# ==========================================================
# PRINT
# ==========================================================

print()
print("========================================")
print("LEAD TIME ANALYSIS")
print("========================================")

print()

if len(lead_df):

    print(
        f"Episodes Found : {len(lead_df)}"
    )

    print(
        f"Mean Lead Time : {lead_df['lead_time_ms'].mean():.2f} ms"
    )

    print(
        f"Median Lead Time : {lead_df['lead_time_ms'].median():.2f} ms"
    )

    print(
        f"Min Lead Time : {lead_df['lead_time_ms'].min():.2f} ms"
    )

    print(
        f"Max Lead Time : {lead_df['lead_time_ms'].max():.2f} ms"
    )

else:

    print(
        "No free_fall -> impact chains found."
    )

print()

print("\nEpisode Counts Per Device:\n")

print(
    lead_df["device_name"]
    .value_counts()
)

print(device_summary)

print()
print(
    f"Saved: {OUTPUT_FILE}"
)