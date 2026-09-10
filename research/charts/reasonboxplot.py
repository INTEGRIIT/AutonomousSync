#!/usr/bin/env python3

"""
===========================================================
ACCELERATION DISTRIBUTION BY EVENT TYPE
===========================================================

PURPOSE
-------
Generate publication-ready acceleration distribution
visualizations with session-aware segmentation.

EXPORTS
-------
1. Session 1 only
2. Sessions 2+ combined

Features:
✓ session detection
✓ session separation
✓ session labels
✓ session shading
✓ publication-ready styling
✓ duplicate-safe cleaning

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

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE_SESSION1 = (
    OUTPUT_DIR /
    "Acceleration_Distribution_Session1.png"
)

OUTPUT_FILE_SESSIONS2PLUS = (
    OUTPUT_DIR /
    "Acceleration_Distribution_Sessions2Plus.png"
)

DPI = 300

TARGET_DEVICE = "Kayla's iPhone"

SESSION_GAP_SECONDS = 300

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
    "reason"
]

for col in required_columns:

    if col not in df.columns:

        raise ValueError(
            f"Missing required column: {col}"
        )

# ===========================================================
# CLEAN DATA
# ===========================================================

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

df["device_name"] = (
    df["device_name"]
    .astype(str)
    .str.strip()
    .str.replace("’", "'", regex=False)
)

df["reason"] = (
    df["reason"]
    .astype(str)
    .str.strip()
    .str.lower()
)

df["feature_acc_norm"] = pd.to_numeric(
    df["feature_acc_norm"],
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
        "reason"
    ]
)

# ===========================================================
# FILTER DEVICE
# ===========================================================

df = df[
    df["device_name"].str.lower()
    == TARGET_DEVICE.lower()
]

# ===========================================================
# REMOVE DUPLICATES
# ===========================================================

df = df.drop_duplicates()

# ===========================================================
# VALID EVENTS
# ===========================================================

valid_events = [
    "stable_window",
    "impact",
    "free_fall"
]

df = df[
    df["reason"].isin(valid_events)
]

# ===========================================================
# SORT CHRONOLOGICALLY
# ===========================================================

df = df.sort_values(
    by="timestamp"
).reset_index(drop=True)

# ===========================================================
# SESSION DETECTION
# ===========================================================

df["time_diff"] = (
    df["timestamp"]
    .diff()
    .dt.total_seconds()
)

df["session_break"] = (
    df["time_diff"]
    > SESSION_GAP_SECONDS
)

df["session_id"] = (
    df["session_break"]
    .cumsum()
    + 1
)

print("\nDetected Sessions:\n")

for session_id in sorted(
    df["session_id"].unique()
):

    rows = len(
        df[df["session_id"] == session_id]
    )

    print(
        f"Session {session_id}: "
        f"{rows} rows"
    )

# ===========================================================
# LABEL MAPPING
# ===========================================================

label_map = {
    "free_fall": "Free Fall",
    "impact": "Impact",
    "stable_window": "Stable"
}

order = [
    "Free Fall",
    "Impact",
    "Stable"
]

# ===========================================================
# COLORS
# ===========================================================

event_colors = {
    "Free Fall": "#7C3AED",
    "Impact": "#DC2626",
    "Stable": "#2563EB"
}

session_backgrounds = {
    1: "#DBEAFE",
    2: "#F3E8FF",
    3: "#DCFCE7",
    4: "#FEF3C7"
}

# ===========================================================
# GENERATE CHART FUNCTION
# ===========================================================

def generate_distribution_chart(
    figure_df,
    output_path,
    figure_title
):

    figure_df = figure_df.copy()

    figure_df["event_label"] = (
        figure_df["reason"]
        .map(label_map)
    )

    unique_sessions = sorted(
        figure_df["session_id"].unique()
    )

    # =======================================================
    # FIGURE SETUP
    # =======================================================

    fig, ax = plt.subplots(
        figsize=(11, 7)
    )

    # =======================================================
    # SESSION SHADING
    # =======================================================

    for session_id in unique_sessions:

        color = session_backgrounds.get(
            session_id,
            "#F3F4F6"
        )

        ax.axhspan(
            ymin=0,
            ymax=1,

            color=color,

            alpha=0.05,

            zorder=0
        )

    # =======================================================
    # BOXPLOTS
    # =======================================================

    box_data = []

    for label in order:

        subset = figure_df[
            figure_df["event_label"]
            == label
        ]

        box_data.append(
            subset["feature_acc_norm"]
        )

    bp = ax.boxplot(
        box_data,

        patch_artist=True,

        widths=0.5,

        showfliers=False
    )

    for patch, label in zip(
        bp["boxes"],
        order
    ):

        patch.set_facecolor(
            event_colors[label]
        )

        patch.set_alpha(0.70)

    # =======================================================
    # SCATTER OVERLAY
    # =======================================================

    for idx, label in enumerate(order):

        subset = figure_df[
            figure_df["event_label"]
            == label
        ]

        x_positions = (
            [idx + 1] * len(subset)
        )

        ax.scatter(
            x_positions,
            subset["feature_acc_norm"],

            color="black",

            alpha=0.25,

            s=16,

            zorder=3
        )

    # =======================================================
    # SESSION LABEL
    # =======================================================

    session_text = (
        "Sessions: "
        + ", ".join(
            [
                str(s)
                for s in unique_sessions
            ]
        )
    )

    ax.text(
        0.99,
        0.97,

        session_text,

        transform=ax.transAxes,

        ha="right",
        va="top",

        fontsize=10,

        bbox=dict(
            facecolor="white",
            edgecolor="gray",
            alpha=0.90
        )
    )

    # =======================================================
    # LABELS
    # =======================================================

    ax.set_title(
        figure_title,
        fontsize=16,
        pad=15
    )

    ax.set_xlabel(
        "Event Trigger",
        fontsize=13
    )

    ax.set_ylabel(
        "Normalized Acceleration",
        fontsize=13
    )

    ax.set_xticks(
        [1, 2, 3]
    )

    ax.set_xticklabels(
        order,
        fontsize=11
    )

    # =======================================================
    # GRID
    # =======================================================

    ax.grid(
        True,
        linestyle="--",
        alpha=0.35
    )

    # =======================================================
    # REMOVE EXTRA WHITESPACE
    # =======================================================

    ax.margins(x=0.02)

    # =======================================================
    # LAYOUT
    # =======================================================

    plt.tight_layout()

    # =======================================================
    # SAVE
    # =======================================================

    plt.savefig(
        output_path,
        dpi=DPI,
        bbox_inches="tight"
    )

    print(
        f"\nSaved:\n{output_path}"
    )

    plt.show()

# ===========================================================
# SESSION 1 ONLY
# ===========================================================

session1_df = df[
    df["session_id"] == 1
]

generate_distribution_chart(
    session1_df,
    OUTPUT_FILE_SESSION1,
    "Acceleration Distribution by Event Trigger — Session 1"
)

# ===========================================================
# SESSIONS 2+ COMBINED
# ===========================================================

sessions2plus_df = df[
    df["session_id"] >= 2
]

generate_distribution_chart(
    sessions2plus_df,
    OUTPUT_FILE_SESSIONS2PLUS,
    "Acceleration Distribution by Event Trigger — Sessions 2+"
)

# ===========================================================
# DONE
# ===========================================================

print("\nDone.\n")