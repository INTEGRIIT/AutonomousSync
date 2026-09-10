#!/usr/bin/env python3

"""
===========================================================
MULTI-SENSOR MOVEMENT FEATURES VISUALIZATION
===========================================================

PURPOSE
-------
Generate a publication-ready multi-sensor motion dynamics
visualization using the full Autonomous Sync dataset across
all devices.

This script creates one combined chart showing:

- normalized acceleration
- jerk
- gyroscope magnitude
- stability

No session filtering is applied. All devices and all valid
records are included in one figure.

===========================================================
"""

import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path

# ===========================================================
# CONFIG
# ===========================================================

INPUT_FILE = "../autosyncRuns.xlsx"

OUTPUT_DIR = Path("./charts")

OUTPUT_FILE = (
    OUTPUT_DIR /
    "Movement_Features_All_Devices.png"
)

DPI = 300

# ===========================================================
# CREATE OUTPUT DIRECTORY
# ===========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ===========================================================
# LOAD DATA
# ===========================================================

print("\nLoading dataset...\n")

df = pd.read_excel(
    INPUT_FILE,
    engine="openpyxl"
)

print(
    f"Loaded rows: {len(df)}"
)

# ===========================================================
# REQUIRED COLUMNS
# ===========================================================

required_columns = [
    "timestamp",
    "device_name",
    "feature_acc_norm",
    "feature_jerk",
    "feature_gyr_norm",
    "feature_stability",
    "reason"
]

for col in required_columns:

    if col not in df.columns:

        raise ValueError(
            f"Missing required column: {col}"
        )

# ===========================================================
# CLEAN DEVICE NAME
# ===========================================================

df["device_name"] = (
    df["device_name"]
    .astype(str)
    .str.strip()
    .str.replace("’", "'", regex=False)
)

# ===========================================================
# CLEAN EVENT LABELS
# ===========================================================

df["reason"] = (
    df["reason"]
    .astype(str)
    .str.strip()
    .str.lower()
)

# ===========================================================
# PARSE TIMESTAMPS
# ===========================================================

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

# ===========================================================
# NUMERIC CONVERSION
# ===========================================================

numeric_columns = [
    "feature_acc_norm",
    "feature_jerk",
    "feature_gyr_norm",
    "feature_stability"
]

for col in numeric_columns:

    df[col] = (
        df[col]
        .astype(str)
        .str.strip()
        .str.replace('"', '', regex=False)
    )

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# ===========================================================
# REMOVE INVALID ROWS
# ===========================================================

df = df.dropna(
    subset=[
        "timestamp",
        "device_name",
        "feature_acc_norm",
        "feature_jerk",
        "feature_gyr_norm",
        "feature_stability",
        "reason"
    ]
)

# ===========================================================
# REMOVE DUPLICATES
# ===========================================================

df = df.drop_duplicates()

# ===========================================================
# SORT CHRONOLOGICALLY
# ===========================================================

df = df.sort_values(
    by="timestamp"
).reset_index(drop=True)

# ===========================================================
# CREATE OBSERVATION INDEX
# ===========================================================

df["observation_index"] = range(
    1,
    len(df) + 1
)

# ===========================================================
# PRINT DATASET SUMMARY
# ===========================================================

print(
    f"\nRows after cleaning: {len(df)}"
)

print(
    f"Unique devices: {df['device_name'].nunique()}"
)

print("\nDevice counts:")
print(
    df["device_name"]
    .value_counts()
)

print("\nEvent counts:")
print(
    df["reason"]
    .value_counts()
)

# ===========================================================
# PLOT CONFIGS
# ===========================================================

plot_configs = [
    (
        "feature_acc_norm",
        "#2563EB",
        "Acceleration",
        "Normalized Acceleration"
    ),
    (
        "feature_jerk",
        "#DC2626",
        "Jerk",
        "Motion Jerk"
    ),
    (
        "feature_gyr_norm",
        "#7C3AED",
        "Gyroscope",
        "Gyroscope Magnitude"
    ),
    (
        "feature_stability",
        "#059669",
        "Stability",
        "Device Stability"
    )
]

# ===========================================================
# FIGURE SETUP
# ===========================================================

fig, axes = plt.subplots(
    4,
    1,
    figsize=(12, 10),
    sharex=True
)

fig.patch.set_facecolor("white")

fig.suptitle(
    "Multi-Sensor Motion Dynamics",
    fontsize=20,
    y=0.985
)

# ===========================================================
# FEATURE PLOTS
# ===========================================================

for idx, (
    column,
    color,
    ylabel,
    title
) in enumerate(plot_configs):

    axes[idx].plot(
        df["observation_index"],
        df[column],
        color=color,
        linewidth=1.5
    )

    axes[idx].set_ylabel(
        ylabel,
        fontsize=11
    )

    axes[idx].set_title(
        title,
        fontsize=13
    )

    axes[idx].grid(
        True,
        linestyle="--",
        alpha=0.35
    )

    axes[idx].margins(x=0)

# ===========================================================
# X-AXIS LABEL
# ===========================================================

axes[3].set_xlabel(
    "Observation Index",
    fontsize=12
)

# ===========================================================
# LAYOUT
# ===========================================================

plt.tight_layout(
    rect=[0, 0, 1, 0.965]
)

# ===========================================================
# SAVE FIGURE
# ===========================================================

plt.savefig(
    OUTPUT_FILE,
    dpi=DPI,
    bbox_inches="tight"
)

print(
    f"\nSaved:\n{OUTPUT_FILE}"
)

# ===========================================================
# SHOW FIGURE
# ===========================================================

plt.show()

# ===========================================================
# DONE
# ===========================================================

print("\nDone.\n")