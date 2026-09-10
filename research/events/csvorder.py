#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_CSV = "eventsd2.csv"
OUTPUT_CSV = "eventsd2_reordered.csv"

# ==========================================================
# REQUIRED COLUMN ORDER
# ==========================================================

COLUMN_ORDER = [

    "event_id",
    "run_number",
    "device_uid",
    "platform",
    "device_name",
    "timestamp",

    "feature_acc_norm",
    "feature_jerk",
    "feature_gyr_norm",
    "feature_roll",
    "feature_pitch",
    "feature_stability",

    "temporal_stable_duration_ms",
    "temporal_free_fall",
    "temporal_impact",
    "temporal_water_emergency",

    "state",
    "event_type",
    "reason",

    "snapshot_id",

    "sync_triggered",
    "push_attempted",
    "push_success",

    "file_count",
    "files",
]

# ==========================================================
# LOAD CSV
# ==========================================================

df = pd.read_csv(INPUT_CSV)

# ==========================================================
# VERIFY COLUMNS EXIST
# ==========================================================

missing = [
    col
    for col in COLUMN_ORDER
    if col not in df.columns
]

if missing:
    print("\nMissing columns:")
    for col in missing:
        print(f"  - {col}")
    raise ValueError("CSV is missing required columns.")

# ==========================================================
# REORDER
# ==========================================================

df = df[COLUMN_ORDER]

# ==========================================================
# SAVE
# ==========================================================

df.to_csv(
    OUTPUT_CSV,
    index=False
)

print(f"\nSaved reordered CSV:")
print(f"  {OUTPUT_CSV}")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")