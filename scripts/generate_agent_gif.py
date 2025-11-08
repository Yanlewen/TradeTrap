#!/usr/bin/env python3
"""Render animated portfolio comparison GIF from agent viewer data."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

# Paths (relative to repo root)
DATA_PATH = Path("agent_viewer/data/agents_data.json")
OUTPUT_PATH = Path("assets/agent-growth.gif")

# Agent configuration: (title, key in json, color)
AGENT_CONFIG: List[Tuple[str, str, str]] = [
    ("Baseline (No Tools)", "deepseek-v3-whole-month", "#f5cb5c"),
    ("With news", "deepseek-v3-whole-month-with-x-and-reddit-1105", "#3480b8"),
    ("Malicious Injection", "deepseek-v3-ReverseExpectations-injection-month", "#c82423"),
]

# Animation tuning
FPS = 20
FRAME_INTERVAL_MS = 45
DENSITY_FACTOR = 5  # multiplier to densify frames for smooth drawing

def _load_agents() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_series(agent_blob: dict) -> Tuple[np.ndarray, np.ndarray]:
    items = sorted(
        agent_blob["positions"].items(),
        key=lambda kv: datetime.strptime(kv[0], "%Y-%m-%d %H:%M:%S"),
    )
    dates = np.array([datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts, _ in items])
    values = np.array([entry["total_asset"] for _, entry in items], dtype=float)
    return mdates.date2num(dates), values


def _light_smooth(values: np.ndarray) -> np.ndarray:
    """Keep line character while removing jagged noise."""
    kernel = np.array([0.2, 0.6, 0.2])
    padded = np.pad(values, (1, 1), mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")
    smoothed[0] = values[0]
    smoothed[-1] = values[-1]
    return smoothed


def build_animation(output_path: Path = OUTPUT_PATH) -> None:
    data = _load_agents()

    series = []
    for label, key, color in AGENT_CONFIG:
        if key not in data:
            raise KeyError(f"Agent key '{key}' not found in {DATA_PATH}")
        dates, values = _extract_series(data[key])
        series.append({"label": label, "dates": dates, "values": values, "color": color})

    # Global timeline
    min_date = min(s["dates"][0] for s in series)
    max_date = max(s["dates"][-1] for s in series)
    num_frames = len(series[0]["dates"]) * DENSITY_FACTOR
    master_dates = np.linspace(min_date, max_date, num_frames)

    for s in series:
        interpolated = np.interp(master_dates, s["dates"], s["values"])
        s["interp_dates"] = master_dates
        s["interp_values"] = _light_smooth(interpolated)

    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor="#0d1421")
    ax.set_facecolor("#0d1421")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.24)

    ax.set_title("Portfolio Value Trajectories", fontsize=15, color="#ffffff", pad=14)
    ax.set_ylabel("Portfolio Value (USD)", fontsize=11, color="#e1e6ff")
    ax.set_xlabel("Date", fontsize=11, color="#e1e6ff")

    all_values = np.concatenate([s["interp_values"] for s in series])
    span = all_values.max() - all_values.min()
    ax.set_ylim(all_values.min() - span * 0.1, all_values.max() + span * 0.08)
    ax.set_xlim(master_dates[0], master_dates[-1])
    ax.grid(True, which="major", color="#27324c", alpha=0.22)

    ax.tick_params(colors="#d7dfff", labelsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    fig.autofmt_xdate(rotation=32, ha="right")

    lines = []
    for s in series:
        (line,) = ax.plot([], [], color=s["color"], linewidth=2.0, label=s["label"])
        lines.append(line)

    legend = ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    for text in legend.get_texts():
        text.set_color("#edf0ff")

    progress_text = ax.text(0.015, 0.91, "", transform=ax.transAxes, fontsize=9.2, color="#9aa5d8")

    def init():
        for line in lines:
            line.set_data([], [])
        progress_text.set_text("")
        return lines + [progress_text]

    def update(frame: int):
        end = frame + 1
        for line, s in zip(lines, series):
            line.set_data(s["interp_dates"][:end], s["interp_values"][:end])
        pct = min((frame + 1) / len(master_dates) * 100.0, 100.0)
        progress_text.set_text(f"Progress {pct:5.1f}%")
        return lines + [progress_text]

    anim = FuncAnimation(fig, update, frames=len(master_dates), init_func=init, interval=FRAME_INTERVAL_MS, blit=False)
    writer = PillowWriter(fps=FPS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(output_path, writer=writer)
    print(f"GIF saved to {output_path}")


if __name__ == "__main__":
    build_animation()
