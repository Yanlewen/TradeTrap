#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Roboto", "DejaVu Sans", "Liberation Sans", "Arial"],
        "axes.titleweight": "bold",
        "axes.labelweight": "bold",
        "font.weight": "medium",
    }
)
AGENT_CONFIG = [
    ("Baseline (No Tools)", "#f5cb5c"),
    ("With news", "#3480b8"),
    ("Malicious Injection", "#c82423"),
]

BASELINE_ENTRY = ("Baseline $5k", "#626d8a", (0, (6, 4)))

OUTPUT_PATH = Path("assets/agent-legend.png")


def build_legend(output_path: Path = OUTPUT_PATH) -> None:
    handles = [
        Line2D([], [], color=color, linewidth=3.6, label=label)
        for label, color in AGENT_CONFIG
    ]
    handles.append(
        Line2D(
            [],
            [],
            color=BASELINE_ENTRY[1],
            linewidth=2.4,
            linestyle=BASELINE_ENTRY[2],
            label=BASELINE_ENTRY[0],
        )
    )

    fig = plt.figure(figsize=(9.0, 2.0), facecolor="#0d1421")
    fig.patch.set_facecolor("#0d1421")
    ax = fig.add_subplot(111)
    ax.axis("off")

    legend = fig.legend(
        handles=handles,
        loc="center",
        ncol=len(handles),
        frameon=False,
        fontsize=16.5,
        labelcolor="#edf0ff",
        columnspacing=1.9,
        handlelength=3.0,
        handletextpad=1.2,
    )

    for text in legend.get_texts():
        text.set_color("#edf0ff")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", transparent=False)
    plt.close(fig)
    print(f"Legend saved to {output_path.resolve()}")


if __name__ == "__main__":
    build_legend()

