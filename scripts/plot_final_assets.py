#!/usr/bin/env python3
"""
生成分组柱状图，对比不同底座模型在多种干预策略下的期末总资产。

数据来源: agent_viewer/data/agents_data.json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "agent_viewer" / "data" / "agents_data.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "assets" / "final_assets_compariso_fake.png"
DEFAULT_BASE_MODELS: List[str] = [
    "deepseek-v3",
    "claude-3.7-sonnet",
    "qwen3-max",
    "gemini-2.5-flash",
    "gpt-5",
]

DEFAULT_OPERATIONS: List[str] = [
    "baseline",
    "whole-month",
    "whole-month-with-x-and-reddit-1105",
    "reverseexpectations-injection-month",
    "fakenews-50%-month",
]

EXCLUDED_OPERATIONS: set[str] = {"attack"}

# 为常见操作预置颜色，可按需扩充；若不足会回退到 matplotlib 默认循环
PALETTE = {
    "baseline": "#c32b23",
    "whole-month": "#fc945d",
    "whole-month-with-x-and-reddit-1105": "#efe9c2",
    "reverseexpectations-injection-month": "#97c3dd",
    "fakenews-50%-month": "#3d67a0",
}


def load_agents(path: Path) -> Dict[str, dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_agent_key(agent_key: str, base_models: Iterable[str]) -> Tuple[str, str]:
    """
    根据命名规则拆出底座模型与操作名称。
    优先匹配用户提供的 base prefix，若失败则退回以首个'-'分割。
    """
    sorted_bases = sorted(base_models, key=len, reverse=True)

    for base in sorted_bases:
        if agent_key == base:
            return base, "baseline"
        prefix = f"{base}-"
        if agent_key.lower().startswith(prefix.lower()):
            op = agent_key[len(prefix) :]
            return base, op or "baseline"

    parts = agent_key.split("-", 1)
    if len(parts) == 2:
        return parts[0], parts[1] or "baseline"
    return agent_key, "baseline"


def build_asset_table(
    agents_data: Dict[str, dict],
    base_models: List[str],
) -> Tuple[List[str], List[str], Dict[str, Dict[str, float]]]:
    assets_map: Dict[str, Dict[str, float]] = defaultdict(dict)
    operations: set[str] = set()

    for agent_key, payload in agents_data.items():
        base, operation = parse_agent_key(agent_key, base_models)
        if operation in EXCLUDED_OPERATIONS:
            continue
        summary = payload.get("summary", {})
        final_asset = float(summary.get("final_total_asset", 0.0))
        assets_map[base][operation] = final_asset
        operations.add(operation)

    # 仅保留出现过的底座，默认顺序按 base_models -> 其余字母顺
    present_bases = [b for b in base_models if assets_map.get(b)]
    for extra in sorted(assets_map.keys()):
        if extra not in present_bases:
            present_bases.append(extra)

    ordered_operations = sorted(operations)

    return present_bases, ordered_operations, assets_map


MOCK_OPERATION_OFFSETS = {
    "baseline": 0,
    "whole-month": 220,
    "whole-month-with-x-and-reddit-1105": 360,
    "reverseexpectations-injection-month": -280,
    "fakenews-50%-month": -120,
}


def inject_mock_data(
    bases: List[str],
    operations: List[str],
    assets_map: Dict[str, Dict[str, float]],
    base_models: List[str],
    baseline_value: float | None,
) -> Tuple[List[str], List[str], Dict[str, Dict[str, float]]]:
    """
    为缺失的底座模型或操作生成伪造数据，便于预览图表外观。
    """
    if baseline_value is None or np.isnan(baseline_value):
        baseline_value = 5000.0

    all_operations = [
        op
        for op in sorted(set(operations).union(DEFAULT_OPERATIONS))
        if op not in EXCLUDED_OPERATIONS
    ]

    for base in base_models:
        base_payload = assets_map.setdefault(base, {})
        rng = np.random.default_rng(abs(hash(base)) % (2**32))

        if "baseline" not in base_payload:
            base_payload["baseline"] = max(
                0.0, baseline_value + rng.normal(0, 180)
            )

        base_baseline = base_payload["baseline"]

        for op in all_operations:
            if op in base_payload:
                continue
            offset = MOCK_OPERATION_OFFSETS.get(op, rng.normal(0, 260))
            jitter = rng.normal(0, 90)
            base_payload[op] = max(0.0, base_baseline + offset + jitter)

    ordered_bases = []
    for base in base_models:
        if base not in ordered_bases:
            ordered_bases.append(base)
    for base in assets_map.keys():
        if base not in ordered_bases:
            ordered_bases.append(base)

    return ordered_bases, all_operations, assets_map


def pick_colors(operations: List[str]) -> List[str]:
    colors: List[str] = []
    default_cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
    cycle_idx = 0
    for op in operations:
        color = PALETTE.get(op.lower()) or PALETTE.get(op)  # 兼容大小写
        if not color:
            if cycle_idx >= len(default_cycle):
                cycle_idx = 0
            color = default_cycle[cycle_idx]
            cycle_idx += 1
        colors.append(color)
    return colors


def plot_grouped_bars(
    bases: List[str],
    operations: List[str],
    assets_map: Dict[str, Dict[str, float]],
    output_path: Path,
    title: str = "Final Portfolio Value Comparison",
    annotate: bool = True,
    baseline_value: float | None = None,
):
    num_bases = len(bases)
    num_ops = len(operations)
    if num_bases == 0 or num_ops == 0:
        raise ValueError("没有可用于绘图的数据，请确认 agents_data.json 内容。")

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
        }
    )

    x = np.arange(num_bases)
    group_width = 0.8
    bar_width = group_width / num_ops

    fig, ax = plt.subplots(figsize=(1.9 * num_bases + 2, 5.5))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#111c2e")
    colors = pick_colors(operations)

    all_values: List[float] = []

    for idx, op in enumerate(operations):
        offsets = x - group_width / 2 + idx * bar_width + bar_width / 2
        heights = [assets_map.get(base, {}).get(op, np.nan) for base in bases]
        bars = ax.bar(offsets, heights, bar_width, label=op, color=colors[idx])

        for val in heights:
            if not np.isnan(val):
                all_values.append(val)

        if annotate:
            for rect, value in zip(bars, heights):
                if not np.isnan(value):
                    if baseline_value is not None and baseline_value != 0:
                        delta_pct = ((value - baseline_value) / baseline_value) * 100
                        label = f"{delta_pct:+.1f}%"
                        if delta_pct > 0:
                            color = "#22c55e"
                        elif delta_pct < 0:
                            color = "#ef4444"
                        else:
                            color = "#e2e8f0"
                    else:
                        label = ""
                        color = "#f8fafc"

                    if label:
                        ax.text(
                            rect.get_x() + rect.get_width() / 2,
                            rect.get_height(),
                            label,
                            ha="center",
                            va="bottom",
                            fontsize=7.5,
                            color=color,
                        )

    if baseline_value is not None:
        ax.axhline(
            baseline_value,
            color="#94a3b8",
            linestyle="--",
            linewidth=1.2,
            alpha=0.85,
            label=f"Baseline {baseline_value:,.0f}",
        )
        all_values.append(baseline_value)

    if all_values:
        min_val = min(all_values)
        max_val = max(all_values)
        if min_val == max_val:
            min_val -= 100
            max_val += 100
        span = max_val - min_val
        padding = max(span * 0.12, 200)
        lower = min_val - padding
        upper = max_val + padding
        ax.set_ylim(lower, upper)

    ax.set_xticks(x)
    ax.set_xticklabels([base.upper() for base in bases], rotation=0, fontsize=11, color="#e2e8f0")
    ax.set_ylabel("Final total asset", fontsize=12, color="#f1f5f9")

    legend = ax.legend(
        title="Operation / Strategy",
        loc="upper center",
        bbox_to_anchor=(0.5, 1.10),
        ncol=min(len(operations) + (1 if baseline_value is not None else 0), 4),
        frameon=True,
        fontsize=9,
    )
    if legend:
        legend.get_title().set_fontsize(10)
        legend.get_title().set_color("#f4f4f5")
        legend.get_frame().set_facecolor("#1e293b")
        legend.get_frame().set_edgecolor("#334155")
        legend.get_frame().set_alpha(0.92)
        for text in legend.get_texts():
            text.set_color("#f8fafc")

    ax.tick_params(colors="#cbd5f5")
    ax.yaxis.label.set_color("#f1f5f9")
    ax.grid(axis="y", linestyle="--", alpha=0.18, color="#1e293b")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    print(f"已生成柱状图: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="对比不同底座模型与策略的期末总资产")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH, help="agents_data.json 路径")
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH, help="输出图像路径")
    parser.add_argument(
        "--bases",
        nargs="*",
        default=DEFAULT_BASE_MODELS,
        help="预期的底座模型前缀，按给定顺序绘制；未列出的模型会自动追加",
    )
    parser.add_argument("--title", type=str, default="Final Portfolio Value Comparison", help="图表标题")
    parser.add_argument("--no-annotate", action="store_true", help="关闭柱体顶部的数值标注")
    parser.add_argument("--baseline", type=float, default=5000.0, help="对比基准资产值，默认 5000")
    parser.add_argument(
        "--mock-missing",
        action="store_true",
        help="为缺失的底座模型或策略补充伪造数据，用于预览图表效果",
    )
    args = parser.parse_args()

    if not args.data_path.exists():
        raise FileNotFoundError(f"找不到数据文件: {args.data_path}")

    agents_data = load_agents(args.data_path)
    bases, operations, assets_map = build_asset_table(agents_data, args.bases)

    if args.mock_missing:
        bases, operations, assets_map = inject_mock_data(
            bases,
            operations,
            assets_map,
            args.bases,
            args.baseline,
        )

    plot_grouped_bars(
        bases,
        operations,
        assets_map,
        args.output_path,
        title=args.title,
        annotate=not args.no_annotate,
        baseline_value=args.baseline,
    )


if __name__ == "__main__":
    main()


