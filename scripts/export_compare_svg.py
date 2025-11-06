#!/usr/bin/env python3
"""Export portfolio comparison chart (dashboard style) to SVG."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "agent_viewer" / "data" / "agents_data.json"
OUTPUT_PATH = BASE_DIR / "assets" / "compare_dashboard.svg"

SERIES_CONFIG: List[Tuple[str, str, str]] = [
    ("Baseline (No Tools)", "deepseek-v3-whole-month", "#ec4899"),  # 粉色
    ("With X & Reddit Tools", "deepseek-v3-whole-month-with-x-and-reddit", "#a855f7"),  # 紫色
    ("With X & Reddit Tools (1105)", "deepseek-v3-whole-month-with-x-and-reddit-1105", "#f59e0b"),  # 橙色
    ("Malicious Injection", "deepseek-v3-ReverseExpectations-injection-month", "#f97316"),  # 深橙
]

plt.rcParams.update({
    "svg.fonttype": "none",
    "font.family": ["Microsoft YaHei", "Segoe UI", "Roboto", "Helvetica Neue", "DejaVu Sans"],
    "font.size": 11,
    "axes.linewidth": 0.8,
})


def _load_raw_series() -> Dict[str, Dict[str, float]]:
    with DATA_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    series = {}
    for _, key, _ in SERIES_CONFIG:
        positions = data[key]["positions"]
        buffer: Dict[str, float] = {}
        for timestamp, payload in positions.items():
            buffer[timestamp] = payload.get("total_asset", buffer.get(timestamp))
        series[key] = buffer
    return series


def _build_union_timeline(series: Dict[str, Dict[str, float]]) -> List[datetime]:
    all_timestamps = set()
    for payload in series.values():
        all_timestamps.update(payload.keys())
    return sorted(datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in all_timestamps)


def _forward_fill(series_map: Dict[str, Dict[str, float]], timeline: List[datetime]) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    aligned = {}
    for _, key, _ in SERIES_CONFIG:
        payload = series_map[key]
        values = []
        last_value = None
        for ts in timeline:
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            if ts_str in payload:
                last_value = payload[ts_str]
            values.append(last_value if last_value is not None else np.nan)
        dates_num = mdates.date2num(timeline)
        aligned[key] = (dates_num, np.array(values, dtype=float))
    return aligned


def _smooth(xs: np.ndarray, ys: np.ndarray, density: int = 6) -> Tuple[np.ndarray, np.ndarray]:
    mask = ~np.isnan(ys)
    xs = xs[mask]
    ys = ys[mask]
    if len(xs) < 2:
        return xs, ys

    dense_x = np.linspace(xs[0], xs[-1], (len(xs) - 1) * density + 1)
    dense_y = np.interp(dense_x, xs, ys)

    kernel = np.array([1, 3, 3, 3, 1], dtype=float)
    kernel /= kernel.sum()
    pad = kernel.size // 2
    padded = np.pad(dense_y, pad_width=pad, mode="edge")
    smoothed_y = np.convolve(padded, kernel, mode="valid")

    return dense_x, smoothed_y


def export_svg() -> None:
    raw_series = _load_raw_series()
    timeline = _build_union_timeline(raw_series)
    aligned = _forward_fill(raw_series, timeline)

    fig, ax = plt.subplots(figsize=(13, 6.8), facecolor="#0b1628")
    fig.subplots_adjust(left=0.07, right=0.98, top=0.9, bottom=0.25)
    ax.set_facecolor("#0b1628")

    # 美化参数
    axis_color = "#b8c2e0"
    grid_color_major = "#243047"
    grid_color_minor = "#1a2336"

    ax.set_title("Portfolio Value Trajectories", fontsize=18, color="white", weight="bold", pad=18)
    ax.set_ylabel("Portfolio Value (USD)", fontsize=12, color=axis_color)
    ax.set_xlabel("Timestamp (Hourly)", fontsize=12, color=axis_color)

    # 自动纵向范围
    all_values = np.concatenate([vals for _, vals in aligned.values()])
    valid_vals = all_values[~np.isnan(all_values)]
    span = valid_vals.max() - valid_vals.min()
    ax.set_ylim(valid_vals.min() - span * 0.05, valid_vals.max() + span * 0.07)

    # 绘制曲线
    for label, key, color in SERIES_CONFIG:
        xs, ys = aligned[key]
        smooth_x, smooth_y = _smooth(xs, ys)
        ax.plot(
            mdates.num2date(smooth_x),
            smooth_y,
            color=color,
            linewidth=2.8,
            label=label,
            alpha=0.9,
        )

    # 坐标与网格
    tick_positions = [ts for ts in timeline if ts.hour in (11, 14)]
    tick_nums = mdates.date2num(tick_positions)
    ax.tick_params(colors=axis_color, labelsize=10)
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=1))
    ax.set_xticks(tick_nums)
    ax.set_xticklabels([ts.strftime("%m/%d %H:%M") for ts in tick_positions], rotation=30, ha="right", color=axis_color)

    ax.grid(True, which="major", color=grid_color_major, linewidth=0.8)
    ax.grid(True, which="minor", color=grid_color_minor, linewidth=0.4, alpha=0.4)

    # 图例样式
    legend = ax.legend(
        loc="upper left",
        frameon=True,
        facecolor="#111c2f",
        edgecolor="#334155",
        fontsize=9.5,
        framealpha=0.9,
    )
    for text in legend.get_texts():
        text.set_color(axis_color)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, format="svg", dpi=220, facecolor=fig.get_facecolor())
    print(f"✅ SVG exported to {OUTPUT_PATH}")


if __name__ == "__main__":
    export_svg()