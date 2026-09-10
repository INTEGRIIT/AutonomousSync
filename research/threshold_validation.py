#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "threshold_validation.xlsx"

# ==========================================================
# TEMPORAL ENGINE THRESHOLDS
# ==========================================================

FREE_FALL_ACC_MAX = 0.5
IMPACT_JERK_MIN = 3.5

# ==========================================================
# LOAD
# ==========================================================

df = pd.read_excel(INPUT_FILE)

# ==========================================================
# CLEANUP
# ==========================================================

df["reason"] = (
    df["reason"]
    .astype(str)
    .str.strip()
    .str.lower()
)

# ==========================================================
# SPLIT EVENTS
# ==========================================================

impact_df = df[
    df["reason"] == "impact"
].copy()

freefall_df = df[
    df["reason"] == "free_fall"
].copy()

stable_df = df[
    df["reason"] == "stable_window"
].copy()

# ==========================================================
# IMPACT VALIDATION
# ==========================================================

impact_pass = impact_df[
    impact_df["feature_jerk"] >= IMPACT_JERK_MIN
]

impact_fail = impact_df[
    impact_df["feature_jerk"] < IMPACT_JERK_MIN
]

impact_total = len(impact_df)

impact_pass_pct = (
    len(impact_pass) / impact_total * 100
    if impact_total
    else 0
)

impact_fail_pct = (
    len(impact_fail) / impact_total * 100
    if impact_total
    else 0
)

# ==========================================================
# FREE FALL VALIDATION
# ==========================================================

freefall_pass = freefall_df[
    freefall_df["feature_acc_norm"] <= FREE_FALL_ACC_MAX
]

freefall_fail = freefall_df[
    freefall_df["feature_acc_norm"] > FREE_FALL_ACC_MAX
]

freefall_total = len(freefall_df)

freefall_pass_pct = (
    len(freefall_pass) / freefall_total * 100
    if freefall_total
    else 0
)

freefall_fail_pct = (
    len(freefall_fail) / freefall_total * 100
    if freefall_total
    else 0
)

# ==========================================================
# STABLE VALIDATION
# ==========================================================

stable_mean_acc = (
    stable_df["feature_acc_norm"]
    .mean()
)

stable_mean_jerk = (
    stable_df["feature_jerk"]
    .mean()
)

stable_mean_stability = (
    stable_df["feature_stability"]
    .mean()
)

# ==========================================================
# SUMMARY
# ==========================================================

summary = pd.DataFrame(
    [
        [
            "Impact Events",
            impact_total
        ],
        [
            "Impact >= 3.5 Jerk",
            len(impact_pass)
        ],
        [
            "Impact < 3.5 Jerk",
            len(impact_fail)
        ],
        [
            "Impact Threshold Pass %",
            impact_pass_pct
        ],

        [
            "Free Fall Events",
            freefall_total
        ],
        [
            "Free Fall <= 0.5g",
            len(freefall_pass)
        ],
        [
            "Free Fall > 0.5g",
            len(freefall_fail)
        ],
        [
            "Free Fall Threshold Pass %",
            freefall_pass_pct
        ],

        [
            "Stable Mean Acc",
            stable_mean_acc
        ],
        [
            "Stable Mean Jerk",
            stable_mean_jerk
        ],
        [
            "Stable Mean Stability",
            stable_mean_stability
        ],
    ],
    columns=[
        "Metric",
        "Value"
    ]
)

# ==========================================================
# EXPORT
# ==========================================================

with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="openpyxl"
) as writer:

    summary.to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

    impact_pass.to_excel(
        writer,
        sheet_name="Impact Pass",
        index=False
    )

    impact_fail.to_excel(
        writer,
        sheet_name="Impact Fail",
        index=False
    )

    freefall_pass.to_excel(
        writer,
        sheet_name="FreeFall Pass",
        index=False
    )

    freefall_fail.to_excel(
        writer,
        sheet_name="FreeFall Fail",
        index=False
    )

# ==========================================================
# CONSOLE OUTPUT
# ==========================================================

print()
print("========================================")
print("THRESHOLD VALIDATION")
print("========================================")

print()
print(
    f"Impact Events: {impact_total}"
)

print(
    f"Impacts >= {IMPACT_JERK_MIN}: "
    f"{len(impact_pass)} "
    f"({impact_pass_pct:.2f}%)"
)

print(
    f"Impacts < {IMPACT_JERK_MIN}: "
    f"{len(impact_fail)} "
    f"({impact_fail_pct:.2f}%)"
)

print()

print(
    f"Free Fall Events: {freefall_total}"
)

print(
    f"Free Falls <= {FREE_FALL_ACC_MAX}g: "
    f"{len(freefall_pass)} "
    f"({freefall_pass_pct:.2f}%)"
)

print(
    f"Free Falls > {FREE_FALL_ACC_MAX}g: "
    f"{len(freefall_fail)} "
    f"({freefall_fail_pct:.2f}%)"
)

print()

print(
    f"Saved: {OUTPUT_FILE}"
)