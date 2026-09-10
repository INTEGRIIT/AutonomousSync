import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
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

state_col = pick_col(["state"])
acc_col = pick_col(["feature_acc_norm", "feature_acc", "acc_norm"])

# -----------------------------
# CLEAN
# -----------------------------
df = df.dropna(subset=[state_col, acc_col]).copy()

# Normalize state labels
df[state_col] = df[state_col].astype(str).str.strip().str.upper()

# 🔥 Remove duplicates (important for your dataset)
df = df.drop_duplicates(subset=["timestamp", acc_col, state_col])

# Map to readable labels
df[state_col] = df[state_col].replace({
    "STILL": "Stable",
    "UNSTABLE": "Unstable"
})

# Keep only relevant states
df = df[df[state_col].isin(["Stable", "Unstable"])]

order = ["Stable", "Unstable"]

# -----------------------------
# STYLE (LOTUS THEME)
# -----------------------------
plt.figure(figsize=(6.5, 4.8))

sns.boxplot(
    x=state_col,
    y=acc_col,
    data=df,
    order=order,
    palette=[
        "#9CA3AF",   # Stable → neutral gray
        "#1F7A4C"    # Unstable → lotus green
    ],
    linewidth=2,
    width=0.5,
    showfliers=False
)

sns.stripplot(
    x=state_col,
    y=acc_col,
    data=df,
    order=order,
    color="black",
    alpha=0.35,
    size=3.2,
    jitter=0.12
)

# -----------------------------
# VISIBILITY FIX
# -----------------------------
plt.ylim(0.2, 2.2)

# -----------------------------
# LABELS
# -----------------------------
plt.title("Acceleration Distribution by Device State", fontsize=15)
plt.xlabel("Device State", fontsize=12.5)
plt.ylabel("Normalized Acceleration", fontsize=12.5)

plt.xticks(fontsize=11.5)
plt.yticks(fontsize=11)

# Clean grid
plt.grid(axis="y", alpha=0.2)

# Remove extra borders
sns.despine()

plt.tight_layout()

# -----------------------------
# SAVE
# -----------------------------
plt.savefig(f"{OUTPUT_DIR}/box_state.png", dpi=300)
plt.close()

print("Final elite state boxplot generated!")