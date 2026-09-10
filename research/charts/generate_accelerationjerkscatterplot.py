#!/usr/bin/env python3

"""
===========================================================
ACCELERATION vs JERK SCATTERPLOT
===========================================================

PURPOSE
-------
Generate a publication-ready scatterplot showing
feature-space separation between:

- stable_window
- impact
- free_fall

X-axis:
    jerk

Y-axis:
    normalized acceleration

UPDATED VERSION
---------------
This version now includes:

✓ session-aware filtering
✓ cleaned publication styling
✓ consistent paper color palette
✓ proper feature-space projection
✓ duplicate-safe preprocessing

This demonstrates that lightweight physics-derived
features can separate motion states without requiring
complex machine learning models.

===========================================================
"""

import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path

# ===========================================================
# CONFIG
# ===========================================================

INPUT_FILE = "../autosyncRuns.csv"

OUTPUT_DIR = Path("./charts")

OUTPUT_FILE = OUTPUT_DIR / (
    "Acceleration_vs_Jerk_Scatterplot.png"
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

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

print(f"Loaded rows: {len(df)}")

# ===========================================================
# REQUIRED COLUMNS
# ===========================================================

required_columns = [
    "timestamp",
    "device_name",
    "feature_acc_norm",
    "feature_jerk",
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
# CLEAN EVENTS
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

df["feature_acc_norm"] = pd.to_numeric(
    df["feature_acc_norm"],
    errors="coerce"
)

df["feature_jerk"] = pd.to_numeric(
    df["feature_jerk"],
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

print(
    f"\nRows after cleaning: {len(df)}"
)

# ===========================================================
# VALID EVENTS
# ===========================================================

valid_events = [
    "stable_window",
    "impact",
    "free_fall"
]

print("\nUnique labels detected:\n")
print(df["reason"].unique())

# ===========================================================
# FILTER EVENT TYPES
# ===========================================================

df = df[
    df["reason"].isin(valid_events)
]

print(
    f"\nRows after event filtering: {len(df)}"
)

print("\nEVENT COUNTS\n")

print(
    df["reason"]
    .value_counts()
)

print(
    f"\nTotal Events: {len(df)}"
)

# ===========================================================
# EVENT COLORS
# ===========================================================

event_colors = {
    "stable_window": "#2563EB",
    "impact": "#DC2626",
    "free_fall": "#7C3AED"
}

# ===========================================================
# FIGURE SETUP
# ===========================================================

fig, ax = plt.subplots(
    figsize=(11, 7)
)

# ===========================================================
# PLOT EACH EVENT TYPE
# ===========================================================

for event_type in valid_events:

    subset = df[
        df["reason"] == event_type
    ]

    print(
        f"{event_type}: {len(subset)} points"
    )

    ax.scatter(
        subset["feature_jerk"],
        subset["feature_acc_norm"],

        label=event_type.replace(
            "_",
            " "
        ).title(),

        color=event_colors[event_type],

        alpha=0.75,

        s=90,

        edgecolors="black",

        linewidths=0.5
    )

# ===========================================================
# LABELS
# ===========================================================

ax.set_xlabel(
    "Jerk",
    fontsize=14
)

ax.set_ylabel(
    "Normalized Acceleration",
    fontsize=14
)

ax.set_title(
    "Acceleration vs Jerk Feature Space",
    fontsize=16,
    pad=15
)

# ===========================================================
# GRID
# ===========================================================

ax.grid(
    True,
    linestyle="--",
    alpha=0.4
)

# ===========================================================
# LEGEND
# ===========================================================

legend = ax.legend(
    title="Event Type",
    fontsize=11
)

legend.get_title().set_fontsize(12)

# ===========================================================
# LAYOUT
# ===========================================================

plt.tight_layout()

# ===========================================================
# SAVE FIGURE
# ===========================================================

plt.savefig(
    OUTPUT_FILE,
    dpi=DPI,
    bbox_inches="tight"
)

print(
    f"\nFigure saved to:\n{OUTPUT_FILE}"
)

# ===========================================================
# SHOW FIGURE
# ===========================================================

plt.show()

# ===========================================================
# DONE
# ===========================================================

print("\nDone.\n")