#!/usr/bin/env python3

import pandas as pd

df = pd.read_excel("autosyncRuns.xlsx")

failed_syncs = df[
    df["sync_triggered"].fillna(0).astype(int) != 1
]

print("\nFAILED SYNC ROWS:")
print(
    failed_syncs[
        [
            "event_id",
            "run_number",
            "device_name",
            "timestamp",
            "state",
            "event_type",
            "reason",
            "sync_triggered",
            "push_attempted",
            "push_success",
        ]
    ]
)

failed_syncs.to_excel(
    "sync_failure_audit.xlsx",
    index=False
)