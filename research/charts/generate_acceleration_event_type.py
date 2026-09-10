#!/usr/bin/env python3

"""
===========================================================
ACCELERATION DISTRIBUTION BY EVENT TYPE
===========================================================

PURPOSE
-------
Generate a publication-ready acceleration distribution
visualization showing statistical separation between:

- stable_window
- impact
- free_fall

UPDATED VERSION
---------------
This version now includes:

✓ session detection logic
✓ session-aware filtering
✓ session background shading
✓ session divider lines
✓ session labels
✓ compressed inactive gaps
✓ consistent styling with motion timeline charts

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

OUTPUT_FILE = OUTPUT_DIR / (
    "Acceleration_Distribution_By_Event_Type.png"
)

DPI = 300

TARGET_DEVICE = "Kayla's iPhone"

SESSION_GAP_SECONDS = 300

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

print(
    f"\nRows for {TARGET_DEVICE}: {len(df)}"
)

# ===========================================================
# SAFETY CHECK
# ===========================================================

if len(df) == 0:

    raise ValueError(
        f"\nNo rows found for device: {TARGET_DEVICE}"
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
# DETECT SESSIONS
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

print(
    f"\nRows after event filtering: {len(df)}"
)
#!/usr/bin/env python3

"""
===========================================================
ACCELERATION DISTRIBUTION BY EVENT TYPE
===========================================================

PURPOSE
-------
Generate a publication-ready acceleration distribution
visualization showing statistical separation between:

- stable_window
- free_fall
- impact

This figure uses the complete experimental dataset
across all devices and all recorded events.

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
    "Acceleration_Distribution_By_Event_Type.png"
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

print(
    f"Loaded rows: {len(df)}"
)

# ===========================================================
# REQUIRED COLUMNS
# ===========================================================

required_columns = [
    "feature_acc_norm",
    "reason"
]

for col in required_columns:

    if col not in df.columns:

        raise ValueError(
            f"Missing required column: {col}"
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
# NUMERIC CONVERSION
# ===========================================================

df["feature_acc_norm"] = pd.to_numeric(
    df["feature_acc_norm"],
    errors="coerce"
)

# ===========================================================
# REMOVE INVALID ROWS
# ===========================================================

df = df.dropna(
    subset=[
        "feature_acc_norm",
        "reason"
    ]
)

# ===========================================================
# REMOVE DUPLICATES
# ===========================================================

df = df.drop_duplicates()

# ===========================================================
# VALID EVENTS
# ===========================================================

valid_events = [
    "stable_window",
    "free_fall",
    "impact"
]

df = df[
    df["reason"].isin(valid_events)
]

# ===========================================================
# EVENT COUNTS
# ===========================================================

print()
print("========================================")
print("ACCELERATION DISTRIBUTION ANALYSIS")
print("========================================")
print()

print(
    df["reason"]
    .value_counts()
)

print()

print(
    f"Total Events: {len(df)}"
)

# ===========================================================
# DATASETS
# ===========================================================

stable_acc = (
    df[
        df["reason"] == "stable_window"
    ]["feature_acc_norm"]
)

freefall_acc = (
    df[
        df["reason"] == "free_fall"
    ]["feature_acc_norm"]
)

impact_acc = (
    df[
        df["reason"] == "impact"
    ]["feature_acc_norm"]
)

# ===========================================================
# SUMMARY STATISTICS
# ===========================================================

summary = pd.DataFrame(
    {
        "event_type": [
            "stable_window",
            "free_fall",
            "impact"
        ],

        "count": [
            len(stable_acc),
            len(freefall_acc),
            len(impact_acc)
        ],

        "mean_acceleration": [
            stable_acc.mean(),
            freefall_acc.mean(),
            impact_acc.mean()
        ],

        "median_acceleration": [
            stable_acc.median(),
            freefall_acc.median(),
            impact_acc.median()
        ],

        "std_acceleration": [
            stable_acc.std(),
            freefall_acc.std(),
            impact_acc.std()
        ]
    }
)

print()
print(summary)
print()

# ===========================================================
# FIGURE SETUP
# ===========================================================

fig, ax = plt.subplots(
    figsize=(8, 6)
)

# ===========================================================
# BOXPLOT
# ===========================================================

box = ax.boxplot(
    [
        stable_acc,
        freefall_acc,
        impact_acc
    ],
    tick_labels=[
        "Stable",
        "Free Fall",
        "Impact"
    ],
    patch_artist=True
)

# ===========================================================
# COLORS
# ===========================================================

colors = [
    "#2563EB",
    "#7C3AED",
    "#DC2626"
]

for patch, color in zip(
    box["boxes"],
    colors
):
    patch.set_facecolor(color)
    patch.set_alpha(0.65)

# ===========================================================
# LABELS
# ===========================================================

ax.set_ylabel(
    "Normalized Acceleration",
    fontsize=13
)

ax.set_title(
    "Acceleration Distribution by Event Type",
    fontsize=15,
    pad=10
)

# ===========================================================
# GRID
# ===========================================================

ax.grid(
    True,
    linestyle="--",
    alpha=0.35
)

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
    f"\nSaved Figure:\n{OUTPUT_FILE}"
)

# ===========================================================
# SHOW FIGURE
# ===========================================================

plt.show()

# ===========================================================
# DONE
# ===========================================================

print("\nDone.\n")
# ===========================================================
# SESSION FILTER
# ===========================================================

df = df[
    df["session_id"] >= 2
]

print(
    f"\nRows after session filtering: {len(df)}"
)

# ===========================================================
# SESSION COLORS
# ===========================================================

session_backgrounds = {
    2: "#F3E8FF",
    3: "#DCFCE7",
    4: "#FEF3C7"
}

# ===========================================================
# EVENT COLORS
# ===========================================================

event_colors = {
    "stable_window": "#2563EB",
    "impact": "#DC2626",
    "free_fall": "#7C3AED"
}

# ===========================================================
# CREATE COMPRESSED TIME AXIS
# ===========================================================

df["relative_time"] = (
    df["timestamp"]
    - df["timestamp"].min()
).dt.total_seconds()

compressed_time = [0]

for i in range(1, len(df)):

    delta = (
        df.iloc[i]["relative_time"]
        - df.iloc[i - 1]["relative_time"]
    )

    if delta > SESSION_GAP_SECONDS:

        delta = 5

    compressed_time.append(
        compressed_time[-1] + delta
    )

df["plot_time"] = compressed_time

# ===========================================================
# SESSION RANGES
# ===========================================================

session_ranges = []

for session_id in sorted(
    df["session_id"].unique()
):

    session_df = df[
        df["session_id"] == session_id
    ]

    start_x = session_df[
        "plot_time"
    ].min()

    end_x = session_df[
        "plot_time"
    ].max()

    session_ranges.append(
        (
            session_id,
            start_x,
            end_x
        )
    )

# ===========================================================
# FIGURE SETUP
# ===========================================================

fig, ax = plt.subplots(
    figsize=(14, 8)
)

# ===========================================================
# SESSION BACKGROUNDS
# ===========================================================

for (
    session_id,
    start_x,
    end_x
) in session_ranges:

    color = session_backgrounds.get(
        session_id,
        "#F3F4F6"
    )

    ax.axvspan(
        start_x,
        end_x,

        color=color,

        alpha=0.18,

        zorder=0
    )

# ===========================================================
# HISTOGRAMS
# ===========================================================

bins = 30

for event_type in valid_events:

    subset = df[
        df["reason"] == event_type
    ]

    print(
        f"{event_type}: {len(subset)} points"
    )

    ax.hist(
        subset["plot_time"],

        bins=bins,

        weights=subset["feature_acc_norm"],

        alpha=0.55,

        color=event_colors[event_type],

        label=event_type.replace(
            "_",
            " "
        ).title(),

        edgecolor="black",

        linewidth=0.5
    )

# ===========================================================
# SESSION LABELS + DIVIDERS
# ===========================================================

for idx, (
    session_id,
    start_x,
    end_x
) in enumerate(session_ranges):

    center_x = (
        start_x + end_x
    ) / 2

    # -------------------------------------------------------
    # LABEL
    # -------------------------------------------------------

    ax.text(
        center_x,
        ax.get_ylim()[1] * 0.93,

        f"Session {session_id}",

        ha="center",
        va="top",

        fontsize=12,

        fontweight="bold",

        bbox=dict(
            facecolor="white",
            edgecolor="black",
            alpha=0.92
        ),

        zorder=10
    )

    # -------------------------------------------------------
    # DIVIDER
    # -------------------------------------------------------

    if idx > 0:

        ax.axvline(
            x=start_x,

            color="black",

            linestyle="--",

            linewidth=1.3,

            alpha=0.75,

            zorder=6
        )

# ===========================================================
# LABELS
# ===========================================================

ax.set_xlabel(
    "Compressed Session-Relative Time",
    fontsize=14
)

ax.set_ylabel(
    "Weighted Acceleration Frequency",
    fontsize=14
)

ax.set_title(
    (
        "Acceleration Distribution by Event Type\n"
        "Sessions 2–4"
    ),
    fontsize=16,
    pad=15
)

# ===========================================================
# GRID
# ===========================================================

ax.grid(
    True,
    linestyle="--",
    alpha=0.35
)

# ===========================================================
# REMOVE X PADDING
# ===========================================================

ax.margins(x=0)

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