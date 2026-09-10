#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "feature_statistics.xlsx"

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

# ==========================================================
# FEATURES TO ANALYZE
# ==========================================================

FEATURES = [
    "feature_acc_norm",
    "feature_jerk",
    "feature_gyr_norm",
    "feature_stability",
    "temporal_stable_duration_ms",
]

# ==========================================================
# EVENT COUNTS
# ==========================================================

event_counts = (
    df["reason"]
    .value_counts()
    .reset_index()
)

event_counts.columns = [
    "event_type",
    "count"
]

# ==========================================================
# FEATURE STATISTICS
# ==========================================================

stats_rows = []

for event_type in sorted(
    df["reason"]
    .dropna()
    .unique()
):

    subset = df[
        df["reason"] == event_type
    ]

    for feature in FEATURES:

        values = pd.to_numeric(
            subset[feature],
            errors="coerce"
        )

        stats_rows.append(
            [
                event_type,
                feature,
                values.count(),
                values.mean(),
                values.std(),
                values.min(),
                values.max(),
            ]
        )

feature_stats = pd.DataFrame(
    stats_rows,
    columns=[
        "event_type",
        "feature",
        "count",
        "mean",
        "std",
        "min",
        "max",
    ]
)

# ==========================================================
# SUMMARY TABLE
# ==========================================================

summary = []

for event_type in sorted(
    df["reason"]
    .dropna()
    .unique()
):

    subset = df[
        df["reason"] == event_type
    ]

    summary.append(
        [
            event_type,
            len(subset),
            subset["feature_acc_norm"].mean(),
            subset["feature_jerk"].mean(),
            subset["feature_gyr_norm"].mean(),
            subset["feature_stability"].mean(),
        ]
    )

summary_df = pd.DataFrame(
    summary,
    columns=[
        "event_type",
        "count",
        "mean_acc_norm",
        "mean_jerk",
        "mean_gyr_norm",
        "mean_stability",
    ]
)

# ==========================================================
# EXPORT
# ==========================================================

with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="openpyxl"
) as writer:

    summary_df.to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

    feature_stats.to_excel(
        writer,
        sheet_name="Feature Statistics",
        index=False
    )

    event_counts.to_excel(
        writer,
        sheet_name="Event Counts",
        index=False
    )

# ==========================================================
# PRINT RESULTS
# ==========================================================

print("\n========================================")
print("FEATURE STATISTICS")
print("========================================")

print("\nEVENT COUNTS")
print(event_counts)

print("\nSUMMARY")
print(summary_df)

print(f"\nSaved: {OUTPUT_FILE}")