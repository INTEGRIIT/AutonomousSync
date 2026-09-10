#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "tp_fp_tn_fn_results.xlsx"

# ==========================================================
# LOAD
# ==========================================================

df = pd.read_excel(INPUT_FILE)

# ==========================================================
# DEVICE-SPECIFIC RUN ID
# ==========================================================

df["device_run_id"] = (
    df["device_name"].astype(str).str.strip()
    + "_run_"
    + df["run_number"].astype(str)
)

print("\nDEVICE RUNS:")
print(
    df["device_run_id"]
    .value_counts()
    .sort_index()
)

# ==========================================================
# DEBUG
# ==========================================================

print("\nREASON VALUES:")
print(df["reason"].value_counts(dropna=False))

print("\nEVENT TYPE VALUES:")
print(df["event_type"].value_counts(dropna=False))

print("\nSAMPLE VALUES:")
print(
    df[
        [
            "device_name",
            "run_number",
            "reason",
            "event_type"
        ]
    ].head(20)
)

# ==========================================================
# GROUND TRUTH
# ==========================================================

df["actual_positive"] = (
    df["reason"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(
        [
            "impact",
            "free_fall"
        ]
    )
)

# ==========================================================
# PREDICTION
# ==========================================================

df["predicted_positive"] = (
    df["event_type"]
    .astype(str)
    .str.strip()
    .str.upper()
    .eq("EMERGENCY")
)

print()
print(
    "Actual Positives:",
    df["actual_positive"].sum()
)

print(
    "Predicted Positives:",
    df["predicted_positive"].sum()
)

print()

# ==========================================================
# TP / FP / TN / FN
# ==========================================================

df["confusion_label"] = df.apply(
    lambda row:
        "TP"
        if row["actual_positive"]
        and row["predicted_positive"]

        else

        "FN"
        if row["actual_positive"]
        and not row["predicted_positive"]

        else

        "FP"
        if not row["actual_positive"]
        and row["predicted_positive"]

        else

        "TN",
    axis=1
)

# ==========================================================
# OVERALL COUNTS
# ==========================================================

counts = (
    df["confusion_label"]
    .value_counts()
)

tp = counts.get("TP", 0)
fp = counts.get("FP", 0)
tn = counts.get("TN", 0)
fn = counts.get("FN", 0)

total = tp + fp + tn + fn

# ==========================================================
# OVERALL METRICS
# ==========================================================

accuracy = (
    (tp + tn) / total
    if total
    else 0
)

precision = (
    tp / (tp + fp)
    if (tp + fp)
    else 0
)

recall = (
    tp / (tp + fn)
    if (tp + fn)
    else 0
)

f1 = (
    2 * precision * recall
    / (precision + recall)
    if (precision + recall)
    else 0
)

# ==========================================================
# SUMMARY TABLE
# ==========================================================

summary = pd.DataFrame(
    [
        ["TP", tp],
        ["FP", fp],
        ["TN", tn],
        ["FN", fn],
        ["Accuracy", accuracy],
        ["Precision", precision],
        ["Recall", recall],
        ["F1 Score", f1],
    ],
    columns=[
        "Metric",
        "Value"
    ]
)

# ==========================================================
# DEVICE RUN COUNTS
# ==========================================================

device_runs = (
    df.groupby("device_name")["run_number"]
      .nunique()
      .reset_index()
)

device_runs.columns = [
    "device_name",
    "unique_runs"
]

print("\nDEVICE RUN COUNTS")
print(device_runs)

# ==========================================================
# PER DEVICE RESULTS
# ==========================================================

device_summary = []

for device in sorted(
    df["device_name"]
    .dropna()
    .unique()
):

    subset = df[
        df["device_name"] == device
    ]

    counts = (
        subset["confusion_label"]
        .value_counts()
    )

    tp_d = counts.get("TP", 0)
    fp_d = counts.get("FP", 0)
    tn_d = counts.get("TN", 0)
    fn_d = counts.get("FN", 0)

    total_d = tp_d + fp_d + tn_d + fn_d

    accuracy_d = (
        (tp_d + tn_d) / total_d
        if total_d else 0
    )

    precision_d = (
        tp_d / (tp_d + fp_d)
        if (tp_d + fp_d)
        else 0
    )

    recall_d = (
        tp_d / (tp_d + fn_d)
        if (tp_d + fn_d)
        else 0
    )

    f1_d = (
        2 * precision_d * recall_d /
        (precision_d + recall_d)
        if (precision_d + recall_d)
        else 0
    )

    device_summary.append(
        [
            device,
            tp_d,
            fp_d,
            tn_d,
            fn_d,
            accuracy_d,
            precision_d,
            recall_d,
            f1_d,
        ]
    )

device_summary = pd.DataFrame(
    device_summary,
    columns=[
        "device_name",
        "TP",
        "FP",
        "TN",
        "FN",
        "Accuracy",
        "Precision",
        "Recall",
        "F1",
    ]
)

# ==========================================================
# ADD UNIQUE RUN COUNTS
# ==========================================================

device_summary = device_summary.merge(
    device_runs,
    on="device_name",
    how="left"
)

device_summary = device_summary[
    [
        "device_name",
        "unique_runs",
        "TP",
        "FP",
        "TN",
        "FN",
        "Accuracy",
        "Precision",
        "Recall",
        "F1",
    ]
]

# ==========================================================
# DATASET SUMMARY
# ==========================================================

dataset_summary = pd.DataFrame(
    [
        [
            df["device_name"].nunique(),
            df["run_number"].nunique(),
            len(df)
        ]
    ],
    columns=[
        "unique_devices",
        "unique_run_numbers",
        "total_events"
    ]
)
# ==========================================================
# PRINT RESULTS
# ==========================================================

print(
    "Saved:",
    OUTPUT_FILE
)

print("\nOVERALL RESULTS")
print(summary)

print("\nPER DEVICE RESULTS")
print(device_summary)