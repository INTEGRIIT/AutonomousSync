#!/usr/bin/env python3

"""
===========================================================
AUTONOMOUS SYNC
ACCELERATION vs JERK FEATURE SEPARATION
===========================================================

PURPOSE
-------
Generate a publication-ready scatterplot showing
feature-space separation between:

- stable_window
- impact
- free_fall

X-axis:
    feature_jerk

Y-axis:
    feature_acc_norm

Color:
    motion event type

This visualization demonstrates that lightweight
physics-derived features naturally separate motion
states without requiring complex machine learning.

Uses:
✓ Full dataset
✓ All devices
✓ CSV input
✓ Duplicate-safe preprocessing
✓ Publication-ready styling
✓ Consistent paper color palette

===========================================================
"""

import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"

OUTPUT_DIR = Path("./charts")

OUTPUT_FILE = (
    OUTPUT_DIR /
    "Acceleration_vs_Jerk_Event_Separation.png"
)

DPI = 300

# ==========================================================
# OUTPUT DIRECTORY
# ==========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("\nLoading dataset...\n")

df = pd.read_excel(
    INPUT_FILE,
    engine="openpyxl"
)

print(
    f"Loaded rows: {len(df)}"
)

# ==========================================================
# REQUIRED COLUMNS
# ==========================================================

required_columns = [
    "feature_acc_norm",
    "feature_jerk",
    "reason"
]

for col in required_columns:

    if col not in df.columns:

        raise ValueError(
            f"Missing required column: {col}"
        )

# ==========================================================
# CLEAN EVENT LABELS
# ==========================================================

df["reason"] = (
    df["reason"]
    .astype(str)
    .str.strip()
    .str.lower()
)

# ==========================================================
# NUMERIC CONVERSION
# ==========================================================

df["feature_acc_norm"] = pd.to_numeric(
    df["feature_acc_norm"],
    errors="coerce"
)

df["feature_jerk"] = pd.to_numeric(
    df["feature_jerk"],
    errors="coerce"
)

# ==========================================================
# REMOVE INVALID ROWS
# ==========================================================

df = df.dropna(
    subset=[
        "feature_acc_norm",
        "feature_jerk",
        "reason"
    ]
)

# ==========================================================
# REMOVE DUPLICATES
# ==========================================================

df = df.drop_duplicates()

print(
    f"\nRows after cleaning: {len(df)}"
)

# ==========================================================
# VALID EVENTS
# ==========================================================

valid_events = [
    "stable_window",
    "impact",
    "free_fall"
]

df = df[
    df["reason"].isin(
        valid_events
    )
]

print(
    f"\nRows after event filtering: {len(df)}"
)

print("\nEvent Counts:\n")

print(
    df["reason"]
    .value_counts()
)

# ==========================================================
# EVENT COLORS
# ==========================================================

event_colors = {
    "stable_window": "#2563EB",
    "impact": "#DC2626",
    "free_fall": "#7C3AED"
}

# ==========================================================
# FIGURE
# ==========================================================

fig, ax = plt.subplots(
    figsize=(10, 7)
)

# ==========================================================
# SCATTERPLOTS
# ==========================================================

for event_type in valid_events:

    subset = df[
        df["reason"] == event_type
    ]

    print(
        f"{event_type}: "
        f"{len(subset)} points"
    )

    ax.scatter(
        subset["feature_jerk"],
        subset["feature_acc_norm"],

        color=event_colors[event_type],

        label=event_type.replace(
            "_",
            " "
        ).title(),

        alpha=0.55,

        s=20,

        edgecolors="none"
    )

# ==========================================================
# LABELS
# ==========================================================

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

# ==========================================================
# GRID
# ==========================================================

ax.grid(
    True,
    linestyle="--",
    alpha=0.35
)

# ==========================================================
# LEGEND
# ==========================================================

legend = ax.legend(
    title="Event Type",
    fontsize=11
)

legend.get_title().set_fontsize(
    12
)

# ==========================================================
# LAYOUT
# ==========================================================

plt.tight_layout()

# ==========================================================
# SAVE
# ==========================================================

plt.savefig(
    OUTPUT_FILE,
    dpi=DPI,
    bbox_inches="tight"
)

print(
    f"\nFigure saved to:\n{OUTPUT_FILE}"
)

# ==========================================================
# SHOW
# ==========================================================

plt.show()

# ==========================================================
# DONE
# ==========================================================

print("\nDone.\n")