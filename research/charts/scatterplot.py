import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# -----------------------------
# CONFIG
# -----------------------------
INPUT_FILE = "../autosyncRuns.csv"
OUTPUT_DIR = "."

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# LOAD + CLEAN
# -----------------------------
df = pd.read_csv(INPUT_FILE)
df.columns = df.columns.str.strip().str.lower()

# -----------------------------
# COLUMN DETECTION
# -----------------------------
def pick_col(options):
    for col in options:
        if col in df.columns:
            return col
    raise ValueError(f"None of these columns found: {options}")

acc_col = pick_col(["feature_acc_norm", "feature_acc", "acc_norm"])
jerk_col = pick_col(["feature_jerk", "jerk"])
event_col = pick_col(["reason", "event_type"])

# -----------------------------
# PREP DATA
# -----------------------------
cols = [acc_col, jerk_col, event_col]
if "timestamp" in df.columns:
    cols.append("timestamp")

scatter_df = df[cols].dropna().copy()

scatter_df[event_col] = (
    scatter_df[event_col]
    .astype(str)
    .str.strip()
    .str.lower()
)

# 🔥 Remove duplicates safely
if "timestamp" in scatter_df.columns:
    scatter_df = scatter_df.drop_duplicates(
        subset=["timestamp", acc_col, jerk_col, event_col]
    )

# Keep only relevant events
valid_events = ["impact", "free_fall", "stable_window"]
scatter_df = scatter_df[scatter_df[event_col].isin(valid_events)]

# -----------------------------
# COLOR + LABEL MAP (LOTUS THEME)
# -----------------------------
colors = {
    "free_fall": "#FFD700",      # yellow
    "impact": "#F59E0B",         # amber/orange
    "stable_window": "#9CA3AF"   # gray
}

labels = {
    "free_fall": "Free Fall",
    "impact": "Impact",
    "stable_window": "Stable"
}

# -----------------------------
# STYLE
# -----------------------------
plt.rcParams.update({
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "legend.fontsize": 10
})

plt.figure(figsize=(6.5, 4.5))

# Deterministic jitter (important for consistency)
np.random.seed(42)

plot_order = ["free_fall", "impact", "stable_window"]

# -----------------------------
# SCATTER PLOT
# -----------------------------
for event in plot_order:
    subset = scatter_df[scatter_df[event_col] == event]
    if subset.empty:
        continue

    jitter = np.random.uniform(-0.05, 0.05, len(subset))

    plt.scatter(
        subset[acc_col],
        subset[jerk_col] + jitter,
        label=labels[event],
        color=colors[event],
        alpha=0.65,
        s=45,
        edgecolors="black",
        linewidth=0.3
    )

# -----------------------------
# VISIBILITY TUNING (CRITICAL)
# -----------------------------
plt.xlim(0.2, 2.2)
plt.ylim(-1, 25)   # 🔥 THIS FIXES YOUR COMPRESSED LOOK

# -----------------------------
# LABELS
# -----------------------------
plt.title("Multi-Feature Separation of Motion Events", fontsize=15)
plt.xlabel("Normalized Acceleration", fontsize=12.5)
plt.ylabel("Jerk (Δ Acceleration)", fontsize=12.5)

plt.xticks(fontsize=11.5)
plt.yticks(fontsize=11)

plt.grid(alpha=0.2)
plt.legend(loc="upper left")

plt.tight_layout()

# -----------------------------
# SAVE
# -----------------------------
plt.savefig(f"{OUTPUT_DIR}/feature_scatter.png", dpi=300)
plt.close()

print("Final elite feature scatter generated!")