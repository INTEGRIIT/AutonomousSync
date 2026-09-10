#!/usr/bin/env python3

"""
===========================================================
AUTONOMOUS SYNC
STATE TRANSITION GRAPH
===========================================================

PURPOSE
-------
Generate a publication-ready state transition graph
showing motion-event flow across the Autonomous Sync
dataset.

State Model:

Stable Window
      ↓
Free Fall
      ↓
Impact
      ↓
Stable Window

Uses:
✓ Full dataset
✓ All devices
✓ XLSX input
✓ Consecutive-state compression
✓ Publication-ready styling

===========================================================
"""

import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

from pathlib import Path

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = "../autosyncRuns.xlsx"

OUTPUT_DIR = Path("./charts")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "State_Transition_Graph.png"
)

DPI = 300

# ==========================================================
# LOAD DATA
# ==========================================================

print("\nLoading dataset...\n")

df = pd.read_excel(
    INPUT_FILE
)

print(
    f"Loaded rows: {len(df)}"
)

# ==========================================================
# REQUIRED COLUMNS
# ==========================================================

required_columns = [
    "timestamp",
    "reason"
]

for col in required_columns:

    if col not in df.columns:

        raise ValueError(
            f"Missing required column: {col}"
        )

# ==========================================================
# CLEAN EVENTS
# ==========================================================

df["reason"] = (
    df["reason"]
    .astype(str)
    .str.strip()
    .str.lower()
)

# ==========================================================
# TIMESTAMP
# ==========================================================

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

# ==========================================================
# REMOVE INVALID
# ==========================================================

df = df.dropna(
    subset=[
        "timestamp",
        "reason"
    ]
)

# ==========================================================
# VALID EVENTS
# ==========================================================

valid_events = [
    "stable_window",
    "free_fall",
    "impact"
]

df = df[
    df["reason"].isin(
        valid_events
    )
]

# ==========================================================
# SORT
# ==========================================================

df = df.sort_values(
    by="timestamp"
).reset_index(
    drop=True
)

# ==========================================================
# COMPRESS CONSECUTIVE STATES
# ==========================================================

compressed_states = []

previous = None

for state in df["reason"]:

    if state != previous:

        compressed_states.append(
            state
        )

    previous = state

print(
    f"\nCompressed states: "
    f"{len(compressed_states)}"
)

# ==========================================================
# BUILD TRANSITIONS
# ==========================================================

transitions = {}

for i in range(
    len(compressed_states) - 1
):

    source = compressed_states[i]

    target = compressed_states[i + 1]

    key = (
        source,
        target
    )

    transitions[key] = (
        transitions.get(
            key,
            0
        ) + 1
    )

print("\nTransitions:\n")

for (
    source,
    target
), count in transitions.items():

    print(
        f"{source} -> {target}: {count}"
    )

# ==========================================================
# GRAPH
# ==========================================================

G = nx.DiGraph()

# ==========================================================
# NODE LABELS
# ==========================================================

node_labels = {
    "stable_window":
        "Stable Window",

    "free_fall":
        "Free Fall",

    "impact":
        "Impact"
}

# ==========================================================
# ADD NODES
# ==========================================================

for node in node_labels:

    G.add_node(node)

# ==========================================================
# ADD EDGES
# ==========================================================

for (
    source,
    target
), count in transitions.items():

    G.add_edge(
        source,
        target,
        weight=count
    )

# ==========================================================
# LAYOUT
# ==========================================================

positions = {

    "stable_window":
        (0.0, 1.0),

    "free_fall":
        (1.2, 1.0),

    "impact":
        (2.4, 1.0)
}

# ==========================================================
# COLORS
# ==========================================================

node_colors = [
    "#2563EB",
    "#7C3AED",
    "#DC2626"
]

# ==========================================================
# FIGURE
# ==========================================================

plt.figure(
    figsize=(10, 4)
)

# ==========================================================
# DRAW NODES
# ==========================================================

nx.draw_networkx_nodes(
    G,
    positions,

    node_color=node_colors,

    node_size=5000,

    edgecolors="black",

    linewidths=1.5
)

# ==========================================================
# DRAW LABELS
# ==========================================================

nx.draw_networkx_labels(
    G,
    positions,

    labels=node_labels,

    font_size=12,

    font_weight="bold",

    font_color="white"
)

# ==========================================================
# DRAW EDGES
# ==========================================================

nx.draw_networkx_edges(
    G,
    positions,

    arrows=True,

    arrowsize=28,

    width=2.5,

    edge_color="gray",

    connectionstyle="arc3,rad=0.1"
)

# ==========================================================
# EDGE COUNTS
# ==========================================================

edge_labels = {}

for (
    source,
    target
), count in transitions.items():

    edge_labels[
        (source, target)
    ] = str(count)

nx.draw_networkx_edge_labels(
    G,
    positions,

    edge_labels=edge_labels,

    font_size=11
)

# ==========================================================
# TITLE
# ==========================================================

plt.title(
    "Autonomous Sync Motion State Transition Model",
    fontsize=16,
    pad=20
)

plt.axis("off")

plt.tight_layout()

# ==========================================================
# SAVE
# ==========================================================

plt.savefig(
    OUTPUT_FILE,
    dpi=DPI,
    bbox_inches="tight"
)

plt.close()

# ==========================================================
# DONE
# ==========================================================

print()
print("Saved:")
print(OUTPUT_FILE)
print()
print("Done.")
print()