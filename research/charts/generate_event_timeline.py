#!/usr/bin/env python3

"""
===========================================================
AUTONOMOUS SYNC
MOTION EVENT TIMELINE
===========================================================

PURPOSE
-------
Generate a publication-ready timeline showing the
distribution of detected motion events across the
entire Autonomous Sync dataset.

Events:
    - stable_window
    - free_fall
    - impact

All devices are included.

No session segmentation.
No device grouping.

===========================================================
"""

import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = "../autosyncRuns.xlsx"

OUTPUT_DIR = Path("./charts")

OUTPUT_FILE = (
    OUTPUT_DIR /
    "Motion_Event_Timeline.png"
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
    INPUT_FILE
)

print(
    f"Loaded rows: {len(df)}"
)

# ==========================================================
# REQUIRED COLUMNS
# ==========================================================

required_columns = [
    "timestamp",
    "reason"
]

for col in required_columns:

    if col not in df.columns:

        raise ValueError(
            f"Missing required column: {col}"
        )

# ==========================================================
# CLEAN
# ==========================================================

df["reason"] = (
    df["reason"]
    .astype(str)
    .str.strip()
    .str.lower()
)

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

# ==========================================================
# REMOVE INVALID ROWS
# ==========================================================

df = df.dropna(
    subset=[
        "timestamp",
        "reason"
    ]
)

# ==========================================================
# VALID EVENTS
# ==========================================================

valid_events = [
    "stable_window",
    "free_fall",
    "impact"
]

df = df[
    df["reason"].isin(
        valid_events
    )
]

# ==========================================================
# REMOVE DUPLICATES
# ==========================================================

df = df.drop_duplicates()

# ==========================================================
# SORT
# ==========================================================

df = df.sort_values(
    by="timestamp"
).reset_index(drop=True)

# ==========================================================
# EVENT INDEX
# ==========================================================

df["event_index"] = range(
    len(df)
)

# ==========================================================
# EVENT MAPPING
# ==========================================================

event_y = {
    "stable_window": 0,
    "free_fall": 1,
    "impact": 2
}

event_colors = {
    "stable_window": "#2563EB",
    "free_fall": "#7C3AED",
    "impact": "#DC2626"
}

df["y"] = (
    df["reason"]
    .map(event_y)
)

# ==========================================================
# FIGURE
# ==========================================================

fig, ax = plt.subplots(
    figsize=(12, 4)
)

# ==========================================================
# TRANSITION LINE
# ==========================================================

ax.plot(
    df["event_index"],
    df["y"],
    color="lightgray",
    linewidth=1.5,
    alpha=0.6,
    zorder=1
)

# ==========================================================
# EVENT POINTS
# ==========================================================

for event_type in valid_events:

    subset = df[
        df["reason"]
        == event_type
    ]

    ax.scatter(
        subset["event_index"],
        subset["y"],

        color=event_colors[event_type],

        label=event_type.replace(
            "_",
            " "
        ).title(),

        s=50,

        alpha=0.85,

        edgecolors="black",

        linewidths=0.4,

        zorder=2
    )

# ==========================================================
# AXES
# ==========================================================

ax.set_yticks(
    [0, 1, 2]
)

ax.set_yticklabels(
    [
        "Stable Window",
        "Free Fall",
        "Impact"
    ]
)

ax.set_xlabel(
    "Event Index",
    fontsize=13
)

ax.set_ylabel(
    "Event Type",
    fontsize=13
)

ax.set_title(
    "Distribution of Detected Motion Events",
    fontsize=15,
    pad=15
)

# ==========================================================
# GRID
# ==========================================================

ax.grid(
    True,
    linestyle="--",
    alpha=0.30
)

# ==========================================================
# LEGEND
# ==========================================================

legend = ax.legend(
    title="Event Type",
    fontsize=10
)

legend.get_title().set_fontsize(
    11
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

print("\nDone.\n")