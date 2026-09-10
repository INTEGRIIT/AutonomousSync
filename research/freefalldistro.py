#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "free_fall_followup_analysis.xlsx"

OUTPUT_DIR = Path("charts")

OUTPUT_FILE = (
    OUTPUT_DIR /
    "Free_Fall_Followup_Distribution.png"
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
    sheet_name="Followup Counts"
)

# ==========================================================
# RENAME FOR PAPER
# ==========================================================

mapping = {
    "free_fall":
        "Continued Free Fall",

    "stable_window":
        "Returned to Stable",

    "impact":
        "Impact",

    "END":
        "End of Session",
}

df["next_event"] = (
    df["next_event"]
    .replace(mapping)
)

# ==========================================================
# PLOT
# ==========================================================

plt.figure(
    figsize=(8, 5)
)

bars = plt.bar(
    df["next_event"],
    df["count"]
)

plt.title(
    "Free-Fall Follow-Up Distribution"
)

plt.xlabel(
    "Next Observed State"
)

plt.ylabel(
    "Event Count"
)

# ==========================================================
# LABELS
# ==========================================================

for bar in bars:

    height = bar.get_height()

    plt.text(
        bar.get_x()
        + bar.get_width() / 2,
        height + 0.5,
        f"{int(height)}",
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
# PRINT
# ==========================================================

print()
print("========================================")
print("FREE FALL FOLLOW-UP DISTRIBUTION")
print("========================================")
print()

print(df)

print()
print(
    f"Saved Figure: {OUTPUT_FILE}"
)