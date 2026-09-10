#!/usr/bin/env python3

"""
===========================================================
AUTONOMOUS SYNC
JERK DISTRIBUTION BY EVENT TYPE
===========================================================

Purpose
-------
Visualize jerk separation between:

- stable_window
- free_fall
- impact

This figure demonstrates how jerk magnitude
changes across motion states and validates
the impact detection threshold.

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
    "Jerk_Distribution_By_Event_Type.png"
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
# DATASETS
# ==========================================================

stable = (
    df[
        df["reason"] == "stable_window"
    ]["feature_jerk"]
    .dropna()
)

freefall = (
    df[
        df["reason"] == "free_fall"
    ]["feature_jerk"]
    .dropna()
)

impact = (
    df[
        df["reason"] == "impact"
    ]["feature_jerk"]
    .dropna()
)

# ==========================================================
# SUMMARY STATS
# ==========================================================

summary = pd.DataFrame(
    [
        [
            "stable_window",
            len(stable),
            stable.mean(),
            stable.median(),
            stable.std(),
            stable.min(),
            stable.max(),
        ],
        [
            "free_fall",
            len(freefall),
            freefall.mean(),
            freefall.median(),
            freefall.std(),
            freefall.min(),
            freefall.max(),
        ],
        [
            "impact",
            len(impact),
            impact.mean(),
            impact.median(),
            impact.std(),
            impact.min(),
            impact.max(),
        ],
    ],
    columns=[
        "event_type",
        "count",
        "mean",
        "median",
        "std",
        "min",
        "max",
    ]
)

# ==========================================================
# PLOT
# ==========================================================

plt.figure(
    figsize=(10, 6)
)

plt.boxplot(
    [
        stable,
        freefall,
        impact,
    ],
    labels=[
        "Stable",
        "Free Fall",
        "Impact",
    ]
)

plt.ylabel(
    "Jerk",
    fontsize=12
)

plt.xlabel(
    "Event Type",
    fontsize=12
)

plt.title(
    "Jerk Distribution by Event Type",
    fontsize=14
)

plt.grid(
    alpha=0.3
)

plt.tight_layout()

# ==========================================================
# SAVE
# ==========================================================

plt.savefig(
    OUTPUT_FILE,
    dpi=DPI,
    bbox_inches="tight"
)

plt.close()

# ==========================================================
# EXPORT STATS
# ==========================================================

summary.to_excel(
    "jerk_distribution_statistics.xlsx",
    index=False
)

# ==========================================================
# CONSOLE OUTPUT
# ==========================================================

print()
print("========================================")
print("JERK DISTRIBUTION ANALYSIS")
print("========================================")
print()

print(summary)

print()
print("Saved Figure:")
print(OUTPUT_FILE)

print()
print("Saved Statistics:")
print("jerk_distribution_statistics.xlsx")