#!/usr/bin/env python3

import pandas as pd

# ==========================================================
# FILES
# ==========================================================

INPUT_CSV = "eventsd2_reordered.csv"
OUTPUT_XLSX = "eventsd2_reordered.xlsx"

# ==========================================================
# LOAD CSV
# ==========================================================

df = pd.read_csv(INPUT_CSV)

# ==========================================================
# SAVE AS EXCEL
# ==========================================================

df.to_excel(
    OUTPUT_XLSX,
    index=False,
    engine="openpyxl"
)

print(f"Saved: {OUTPUT_XLSX}")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")