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
# LOAD
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
    raise ValueError(f"Missing columns: {options}")

time_col = pick_col(["timestamp"])
state_col = pick_col(["state"])
event_col = pick_col(["reason", "event_type"])

# -----------------------------
# CLEAN DATA
# -----------------------------
df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
df = df.dropna(subset=[time_col, state_col])

df = df.sort_values(time_col)

df[state_col] = df[state_col].str.upper()
df[event_col] = df[event_col].str.lower()

# -----------------------------
# MAP STATES (Y-AXIS)
# -----------------------------
state_map = {
    "STILL": 0,
    "MOVING": 1,
    "UNSTABLE": 2
}

df["state_num"] = df[state_col].map(state_map)
df = df.dropna(subset=["state_num"])

# -----------------------------
# COLOR MAP (REASON)
# -----------------------------
colors = {
    "impact": "#f97316",
    "free_fall": "#ef4444",
    "unstable": "#22c55e",
    "stable_window": "#9ca3af"
}

# -----------------------------
# PLOT
# -----------------------------
plt.figure(figsize=(7,4))

for event, group in df.groupby(event_col):
    plt.scatter(
        group[time_col],
        group["state_num"] + np.random.uniform(-0.05, 0.05, len(group)),  # jitter
        label=event.replace("_", " ").title(),
        color=colors.get(event, "#3b82f6"),
        alpha=0.7,
        s=35
    )

# -----------------------------
# AXIS LABELS
# -----------------------------
plt.yticks(
    [0, 1, 2],
    ["Still", "Moving", "Unstable"]
)

plt.xlabel("Time")
plt.ylabel("Device State")
plt.title("Temporal Sequence of Device States and Event Triggers")

plt.legend(loc="upper left")
plt.grid(alpha=0.2)
plt.tight_layout()

# -----------------------------
# SAVE
# -----------------------------
plt.savefig(f"{OUTPUT_DIR}/event_timeline.png", dpi=300)
plt.close()

print("Timeline chart generated!")