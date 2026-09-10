#!/usr/bin/env python3

import pandas as pd

INPUT_FILE = "autosyncRunsV1.xlsx"
OUTPUT_FILE = "tp_fp_tn_fn_results.xlsx"

df = pd.read_excel(INPUT_FILE)

# normalize TRUE/FALSE values safely
def to_bool(value):
    return str(value).strip().upper() == "TRUE"

df["actual_impact"] = df["temporal_impact"].apply(to_bool)
df["predicted_push_success"] = df["push_success"].apply(to_bool)

# TP / FP / TN / FN
df["confusion_label"] = df.apply(
    lambda row:
        "TP" if row["actual_impact"] and row["predicted_push_success"] else
        "FN" if row["actual_impact"] and not row["predicted_push_success"] else
        "FP" if not row["actual_impact"] and row["predicted_push_success"] else
        "TN",
    axis=1
)

# counts
counts = df["confusion_label"].value_counts()

tp = counts.get("TP", 0)
fp = counts.get("FP", 0)
tn = counts.get("TN", 0)
fn = counts.get("FN", 0)

total = tp + fp + tn + fn

accuracy = (tp + tn) / total if total else 0
precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0
f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0

summary = pd.DataFrame([
    ["TP", tp],
    ["FP", fp],
    ["TN", tn],
    ["FN", fn],
    ["Accuracy", accuracy],
    ["Precision", precision],
    ["Recall", recall],
    ["F1 Score", f1],
], columns=["Metric", "Value"])

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Labeled Results", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

print("Saved:", OUTPUT_FILE)
print()
print(summary)