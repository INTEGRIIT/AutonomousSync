import pandas as pd
import matplotlib.pyplot as plt
import os

# -----------------------------
# CONFIG
# -----------------------------
INPUT_FILE = "../autosyncRuns.csv"
OUTPUT_DIR = "charts"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# LOAD DATA
# -----------------------------
df = pd.read_csv(INPUT_FILE)
df.columns = df.columns.str.strip().str.lower()

# -----------------------------
# COLUMN DETECTION
# -----------------------------
event_col = "reason" if "reason" in df.columns else "event_type"

# -----------------------------
# CLEAN DATA
# -----------------------------
df = df.dropna(subset=[event_col]).copy()
df[event_col] = df[event_col].astype(str).str.strip().str.lower()

# 🔥 Remove duplicates (important for your dataset)
if "timestamp" in df.columns:
    df = df.drop_duplicates(subset=["timestamp", event_col])

# Keep only meaningful events
df = df[df[event_col].isin(["free_fall", "impact", "stable_window"])]

# Map labels
df[event_col] = df[event_col].replace({
    "free_fall": "Free Fall",
    "impact": "Impact",
    "stable_window": "Stable"
})

# -----------------------------
# EVENT DISTRIBUTION
# -----------------------------
order = ["Free Fall", "Impact", "Stable"]
event_counts = df[event_col].value_counts().reindex(order)

# -----------------------------
# STYLE (LOTUS THEME)
# -----------------------------
colors = [
    "#FFD700",  # Free Fall → yellow
    "#F59E0B",  # Impact → orange
    "#9CA3AF"   # Stable → gray
]

plt.figure(figsize=(6.5, 4.5))

bars = plt.bar(order, event_counts, color=colors)

# Add count labels on bars
for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{int(height)}",
        ha="center",
        va="bottom",
        fontsize=11
    )

# -----------------------------
# LABELS
# -----------------------------
plt.title("Distribution of Detected Motion Events", fontsize=15)
plt.xlabel("Event Type", fontsize=12.5)
plt.ylabel("Count", fontsize=12.5)

plt.xticks(fontsize=11.5)
plt.yticks(fontsize=11)

plt.grid(axis="y", alpha=0.2)

plt.tight_layout()

# -----------------------------
# SAVE
# -----------------------------
plt.savefig(f"{OUTPUT_DIR}/event_distribution.png", dpi=300)
plt.close()

print("Elite event distribution chart generated!")