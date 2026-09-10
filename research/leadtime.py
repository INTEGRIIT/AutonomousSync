#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "lead_time_analysis.xlsx"

OUTPUT_DIR = Path("charts")

OUTPUT_FILE = (
    OUTPUT_DIR /
    "Lead_Time_Histogram.png"
)

# ==========================================================
# OUTPUT DIR
# ==========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ==========================================================
# LOAD
# ==========================================================

df = pd.read_excel(
    INPUT_FILE,
    sheet_name="Lead Times"
)

# ==========================================================
# BINS (PAPER FRIENDLY)
# ==========================================================

bins = [
    0,
    500,
    2000,
    5000,
    10000
]

labels = [
    "<0.5 sec",
    "0.5-2 sec",
    "2-5 sec",
    "5-10 sec"
]


df["lead_time_bin"] = pd.cut(
    df["lead_time_ms"],
    bins=bins,
    labels=labels,
    include_lowest=True
)

hist_df = (
    df["lead_time_bin"]
    .value_counts()
    .sort_index()
    .reset_index()
)

hist_df.columns = [
    "lead_time_range",
    "count"
]

# ==========================================================
# PLOT
# ==========================================================

plt.figure(
    figsize=(9, 5)
)

bars = plt.bar(
    hist_df["lead_time_range"],
    hist_df["count"],

    color="#2563EB",      # Autonomous Sync blue
    edgecolor="black",
    linewidth=0.8
)

plt.title(
    f"Free-Fall to Impact Detection Intervals (n={len(df)})",
    fontsize=14,
    pad=12
)

plt.xlabel(
    "Lead Time Range",
    fontsize=12
)

plt.ylabel(
    "Number of Events",
    fontsize=12
)

plt.grid(
    axis="y",
    linestyle="--",
    alpha=0.35
)

plt.xlabel(
    "Lead Time Range"
)

plt.ylabel(
    "Number of Events"
)

# ==========================================================
# LABELS
# ==========================================================

for bar in bars:

    height = bar.get_height()

    plt.text(
        bar.get_x()
        + bar.get_width() / 2,
        height + 0.05,
        str(int(height)),
        ha="center"
    )

# ==========================================================
# SAVE
# ==========================================================

plt.tight_layout()

plt.savefig(
    OUTPUT_FILE,
    dpi=300,
    bbox_inches="tight"
)

plt.close()

# ==========================================================
# EXPORT DATA
# ==========================================================

hist_df.to_excel(
    "lead_time_histogram_data.xlsx",
    index=False
)

# ==========================================================
# PRINT
# ==========================================================

print()
print("========================================")
print("LEAD TIME HISTOGRAM")
print("========================================")
print()

print(hist_df)

print()

print(
    f"Saved Figure: {OUTPUT_FILE}"
)

print(
    "Saved Data: lead_time_histogram_data.xlsx"
)