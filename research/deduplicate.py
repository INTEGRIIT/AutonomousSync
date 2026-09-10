#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_FILE = "autosyncRuns.xlsx"
OUTPUT_FILE = "autosyncRuns_deduplicated.xlsx"

# ==========================================================
# LOAD
# ==========================================================

df = pd.read_excel(INPUT_FILE)

print(f"Original Rows: {len(df)}")

# ==========================================================
# REMOVE DUPLICATES
# ==========================================================

before = len(df)

df = df.drop_duplicates(
    subset=["event_id"],
    keep="first"
)

after = len(df)

removed = before - after

# ==========================================================
# SAVE
# ==========================================================

df.to_excel(
    OUTPUT_FILE,
    index=False,
    engine="openpyxl"
)

print(f"Rows After Deduplication: {after}")
print(f"Duplicates Removed: {removed}")
print(f"Saved: {OUTPUT_FILE}")