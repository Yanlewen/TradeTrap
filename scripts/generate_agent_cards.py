#!/usr/bin/env python3
"""根据 agents_data.json 生成类似 trade-bench 卡片风格的比较图。"""

from __future__ import annotations

import argparse
import json
import re
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib import patches

# 默认路径与参数
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "agent_viewer" / "data" / "agents_data.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "assets" / "agent_cards"


PALETTE = [
    "#ef4444",
    "#f97316",
    "#facc15",
    "#22c55e",
    "#14b8a6",
    "#0ea5e9",
    "#6366f1",
    "#a855f7",
    "#64748b",
]


def load_agents(data_path: Path) -> Dict[str, dict]:
    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compute_return(summary: dict) -> float:
    initial_cash = summary.get("initial_cash", 0) or 0
    final_asset = summary.get("final_total_asset", initial_cash)
    if initial_cash == 0:
        return 0.0
    return (final_asset / initial_cash - 1) * 100


def extract_latest_positions(agent_data: dict) -> Tuple[str | None, dict]:
    positions = agent_data.get("positions", {})
    if not positions:
        return None, {}
    latest_ts = max(positions.keys())
    return latest_ts, positions[latest_ts]


def extract_allocation_from_logs(agent_data: dict) -> Tuple[Dict[str, float], str | None]:
    logs = agent_data.get("logs", {})
    if not logs:
        return {}, None

    latest_log_ts = max(logs.keys())
    entries = logs[latest_log_ts]
    bullet_pattern = re.compile(
        r"^\s*[-•]\s*\*\*(?P<symbol>[A-Z]{2,})\*\*[^$]*\$\s*(?P<value>[0-9,]+(?:\.\d+)?)",
        re.MULTILINE,
    )

    for entry in reversed(entries):
        for message in reversed(entry.get("new_messages", [])):
            if isinstance(message, dict):
                content = message.get("content", "")
            elif isinstance(message, str):
                content = message
            else:
                continue
            matches = bullet_pattern.findall(content)
            if not matches:
                continue

            allocation: Dict[str, float] = {}
            for symbol, value_str in matches:
                symbol = symbol.upper()
                if symbol == "TOTAL":
                    continue
                value = float(value_str.replace(",", ""))
                if value <= 0:
                    continue
                allocation[symbol] = value

            if allocation:
                return allocation, latest_log_ts

    return {}, latest_log_ts


def fallback_allocation(agent_data: dict) -> Tuple[Dict[str, float], str | None]:
    latest_ts, latest_position = extract_latest_positions(agent_data)
    if not latest_position:
        return {}, latest_ts

    holdings = latest_position.get("positions", {})
    if not holdings:
        return {}, latest_ts

    cash = float(holdings.get("CASH", 0.0) or 0.0)
    total_asset = float(
        latest_position.get("total_asset")
        or agent_data.get("summary", {}).get("final_total_asset", cash)
        or 0.0
    )

    symbol_values: Dict[str, float] = {}
    invested = max(total_asset - cash, 0.0)
    share_count = sum(v for k, v in holdings.items() if k != "CASH" and isinstance(v, (int, float)) and v > 0)

    if share_count > 0 and invested > 0:
        avg_price = invested / share_count
    else:
        avg_price = 0.0

    for symbol, quantity in holdings.items():
        if symbol == "CASH":
            continue
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            continue
        if avg_price > 0:
            symbol_values[symbol] = quantity * avg_price
        else:
            symbol_values[symbol] = float(quantity)

    if cash > 0:
        symbol_values["CASH"] = cash

    return symbol_values, latest_ts


def get_asset_allocation(agent_data: dict) -> Tuple[List[Tuple[str, float]], str | None]:
    allocation, ts = extract_allocation_from_logs(agent_data)

    non_cash_keys = [k for k in allocation if k.upper() != "CASH"]
    if not allocation or not non_cash_keys:
        fallback, ts = fallback_allocation(agent_data)
        if fallback:
            allocation = fallback

    if not allocation:
        return [], ts

    total = sum(allocation.values())
    if total <= 0:
        return [], ts

    sorted_items = sorted(allocation.items(), key=lambda x: x[1], reverse=True)
    normalized = [(symbol, value / total) for symbol, value in sorted_items]
    return normalized, ts


def draw_card(ax, agent_title: str, return_pct: float, allocation: List[Tuple[str, float]]):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # 卡片背景
    card = patches.FancyBboxPatch(
        (0.02, 0.02),
        0.96,
        0.96,
        boxstyle="round,pad=0.015",
        linewidth=0,
        facecolor="#1f2937",
    )
    ax.add_patch(card)

    ax.text(0.08, 0.82, agent_title, color="white", fontsize=13, fontweight="bold", ha="left", va="top", wrap=True)

    ax.text(0.08, 0.63, "RETURN", color="#9ca3af", fontsize=9, ha="left")

    ax.text(
        0.08,
        0.5,
        f"{return_pct:.1f}%",
        color="#f59e0b",
        fontsize=26,
        fontweight="bold",
        ha="left",
    )

    ax.text(0.08, 0.33, "ASSET ALLOCATION", color="#9ca3af", fontsize=9, ha="left")

    bar_left, bar_bottom, bar_width, bar_height = 0.08, 0.2, 0.84, 0.09

    # 背景条
    bar_bg = patches.FancyBboxPatch(
        (bar_left, bar_bottom),
        bar_width,
        bar_height,
        boxstyle="round,pad=0.01",
        linewidth=0,
        facecolor="#111827",
    )
    ax.add_patch(bar_bg)

    if allocation:
        current_x = bar_left
        for idx, (symbol, frac) in enumerate(allocation):
            width = bar_width * frac
            # 避免浮点误差累积导致条形不到头
            if idx == len(allocation) - 1:
                width = bar_left + bar_width - current_x
            color = PALETTE[idx % len(PALETTE)]
            segment = patches.Rectangle(
                (current_x, bar_bottom),
                width,
                bar_height,
                linewidth=0,
                facecolor=color,
            )
            ax.add_patch(segment)
            current_x += width

        # 仅展示前三个权重文字
        info_items = [f"{symbol} {frac * 100:,.0f}%" for symbol, frac in allocation[:3]]
        if info_items:
            caption = textwrap.fill(" | ".join(info_items), width=32)
            ax.text(bar_left, 0.1, caption, color="#d1d5db", fontsize=8, ha="left", va="top")


def format_agent_title(agent_key: str) -> str:
    tokens = [seg.capitalize() for seg in agent_key.replace("-", " ").split()]
    title = " ".join(tokens)
    return textwrap.fill(title, width=20)


def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z_-]+", "_", name)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "agent"


def main():
    parser = argparse.ArgumentParser(description="生成Agent卡片比较图")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH, help="agents_data.json 路径")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="输出图片目录")
    parser.add_argument("--output-path", type=Path, default=None, help="单个 agent 时使用的输出文件")
    parser.add_argument(
        "--agents",
        nargs="*",
        default=None,
        help="需要展示的 agent 名称，默认展示文件中的前三个",
    )
    args = parser.parse_args()

    data_path = args.data_path
    if not data_path.exists():
        raise FileNotFoundError(f"找不到数据文件: {data_path}")

    agents_data = load_agents(data_path)

    selected_agents = args.agents or list(agents_data.keys())[:3]
    if not selected_agents:
        raise ValueError("未找到任何 agent 数据")

    if args.output_path and len(selected_agents) != 1:
        raise ValueError("仅在选择单个 agent 时才允许使用 --output-path")

    plt.rcParams["figure.facecolor"] = "#0f172a"
    plt.rcParams["axes.facecolor"] = "#0f172a"
    plt.rcParams["savefig.facecolor"] = "#0f172a"

    output_dir = args.output_path.parent if args.output_path and len(selected_agents) == 1 else args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for agent_key in selected_agents:
        fig, ax = plt.subplots(figsize=(3.2, 4.5))
        agent_data = agents_data.get(agent_key)
        if agent_data is None:
            ax.axis("off")
            ax.text(0.5, 0.5, f"缺少 {agent_key} 数据", color="white", ha="center", va="center")
        else:
            summary = agent_data.get("summary", {})
            return_pct = compute_return(summary)
            allocation, _ = get_asset_allocation(agent_data)
            draw_card(ax, format_agent_title(agent_key), return_pct, allocation)

        plt.tight_layout()

        if args.output_path and len(selected_agents) == 1:
            output_file = args.output_path
        else:
            file_name = f"{sanitize_filename(agent_key)}.png"
            output_file = output_dir / file_name

        fig.savefig(output_file, dpi=220, bbox_inches="tight")
        plt.close(fig)
        print(f"已生成图片: {output_file}")


if __name__ == "__main__":
    main()


