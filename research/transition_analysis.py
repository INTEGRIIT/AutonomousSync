#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "transition_analysis.xlsx"

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

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

# ==========================================================
# SORT
# ==========================================================

df = df.sort_values(
    [
        "device_name",
        "timestamp"
    ]
).reset_index(drop=True)

# ==========================================================
# NEXT EVENT PER DEVICE
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
# TIME DELTA
# ==========================================================

df["delta_seconds"] = (
    df["next_timestamp"]
    - df["timestamp"]
).dt.total_seconds()

# ==========================================================
# TRANSITION LABEL
# ==========================================================

df["transition"] = (
    df["reason"]
    + " -> "
    + df["next_reason"].fillna("END")
)

# ==========================================================
# TRANSITION COUNTS
# ==========================================================

transition_counts = (
    df["transition"]
    .value_counts()
    .reset_index()
)

transition_counts.columns = [
    "transition",
    "count"
]

# ==========================================================
# COMMON TRANSITIONS
# ==========================================================

interesting = [
    "stable_window -> free_fall",
    "free_fall -> impact",
    "stable_window -> impact",
    "impact -> stable_window",
    "impact -> free_fall",
    "free_fall -> stable_window",
]

interesting_transitions = (
    transition_counts[
        transition_counts["transition"]
        .isin(interesting)
    ]
    .sort_values(
        "count",
        ascending=False
    )
)

# ==========================================================
# TRANSITION TIMING
# ==========================================================

transition_timing = (
    df.groupby("transition")["delta_seconds"]
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
# DEVICE TRANSITIONS
# ==========================================================

device_transitions = (
    df.groupby(
        [
            "device_name",
            "transition"
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

    transition_counts.to_excel(
        writer,
        sheet_name="All Transitions",
        index=False
    )

    interesting_transitions.to_excel(
        writer,
        sheet_name="Key Transitions",
        index=False
    )

    transition_timing.to_excel(
        writer,
        sheet_name="Transition Timing",
        index=False
    )

    device_transitions.to_excel(
        writer,
        sheet_name="Per Device",
        index=False
    )

# ==========================================================
# PRINT RESULTS
# ==========================================================

print()
print("======================================")
print("TRANSITION ANALYSIS")
print("======================================")

print()
print("KEY TRANSITIONS")
print(
    interesting_transitions
)

print()
print("TOP 20 TRANSITIONS")
print(
    transition_counts.head(20)
)

print()
print(
    f"Saved: {OUTPUT_FILE}"
)