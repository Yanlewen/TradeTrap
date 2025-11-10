#!/usr/bin/env python3
"""Calculate final portfolio values from position records and price data, then plot bar charts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "assets" / "final_assets_from_positions1.png"

DEFAULT_BASE_MODELS: List[str] = [
    "deepseek-v3",
    "claude-3.7-sonnet",
    "qwen3-max",
    "gemini-2.5-flash",
    "gpt-5",
]

DEFAULT_OPERATIONS: List[str] = [
    "normal",
    "injection",
]

MODEL_SOURCES: Dict[str, Dict[str, str]] = {
    "deepseek-v3": {
        "normal": "data/agent_data/deepseek/deepseek-v3-whole-month-with-x-and-reddit-1105/position/position.jsonl",
        "injection": "data/agent_data/deepseek/deepseek-v3-ReverseExpectations-injection-month/position/position.jsonl",
    },
    "claude-3.7-sonnet": {
        "normal": "data/agent_data/claude/claude-3.7-sonnet/position/position.jsonl",
        "injection": "data/agent_data/claude/claude-3.7-sonnet-ReverseExpectations/position/position.jsonl",
    },
    "qwen3-max": {
        "normal": "data/agent_data/qwen/qwen3-max-with-news/position/position.jsonl",
        "injection": "data/agent_data/qwen/qwen3-max-ReverseExpectations/position/position.jsonl",
    },
    "gemini-2.5-flash": {
        "normal": "data/agent_data/gemini/gemini-2.5-flash-with-news-1108/position/position.jsonl",
        "injection": "data/agent_data/gemini/gemini-2.5-flash-ReverseExpectations/position/position.jsonl",
    },
    "gpt-5": {
        "normal": "data/agent_data/gpt/gpt-5/position/position.jsonl",
        "injection": "data/agent_data/gpt/gpt-5-ReverseExpectations/position/position.jsonl",
    },
}

COLORS = ["#d01443", "#038349"]
INITIAL_CASH_FALLBACK = 5000.0
PLACEHOLDER_ASSET_VALUE = 5000.0


@dataclass
class FinalAssetRecord:
    base_model: str
    operation: str
    value: float
    initial_cash: float
    percent_change: float
    missing_symbols: List[str]
    source_path: Optional[Path]


def _load_jsonl(path: Path) -> List[dict]:
    entries: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} 中存在无法解析的 JSON 行: {exc}") from exc
    return entries


def _load_price_data(symbol: str, cache: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    if symbol in cache:
        return cache[symbol]

    price_file = DATA_ROOT / f"daily_prices_{symbol}.json"
    if not price_file.exists():
        raise FileNotFoundError(f"Price data file not found for {symbol}: {price_file}")

    with price_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    time_series: Optional[Dict[str, Dict[str, str]]] = None
    if "Time Series (60min)" in payload:
        time_series = payload["Time Series (60min)"]
    elif "Time Series (Daily)" in payload:
        time_series = payload["Time Series (Daily)"]
    elif isinstance(payload, dict):
        time_series = payload

    prices: Dict[str, float] = {}
    if time_series:
        for ts_key, values in time_series.items():
            if isinstance(values, dict):
                close_value = (
                    values.get("4. close")
                    or values.get("close")
                    or values.get("Close")
                )
                if close_value is None:
                    continue
                try:
                    prices[ts_key] = float(close_value)
                except (TypeError, ValueError):
                    continue
            else:
                try:
                    prices[ts_key] = float(values)
                except (TypeError, ValueError):
                    continue

    cache[symbol] = prices
    return prices


def _get_stock_price(
    symbol: str,
    date_str: str,
    cache: Dict[str, Dict[str, float]],
) -> Optional[float]:
    prices = _load_price_data(symbol, cache)
    if not prices:
        return None

    if date_str in prices:
        return prices[date_str]

    date_part = date_str.split(" ")[0]
    same_day = {k: v for k, v in prices.items() if k.startswith(date_part)}
    if same_day:
        latest_key = max(same_day.keys())
        return same_day[latest_key]

    earlier_keys = [k for k in prices if k <= date_str]
    if earlier_keys:
        return prices[max(earlier_keys)]

    return None


def _compute_final_asset(
    base_model: str,
    operation: str,
    position_path: Path,
    price_cache: Dict[str, Dict[str, float]],
) -> FinalAssetRecord:
    entries = _load_jsonl(position_path)
    if not entries:
        raise ValueError(f"{position_path} has no position records.")

    first_positions = entries[0].get("positions", {}) or {}
    initial_cash = float(first_positions.get("CASH", INITIAL_CASH_FALLBACK))

    final_entry = entries[-1]
    positions = final_entry.get("positions", {}) or {}
    cash = float(positions.get("CASH", initial_cash))
    date_str = final_entry.get("date")
    if not date_str:
        raise ValueError(f"{position_path} has no date field in the last record.")

    total_asset = cash
    missing_symbols: List[str] = []

    for symbol, quantity in positions.items():
        if symbol == "CASH":
            continue
        try:
            qty = float(quantity)
        except (TypeError, ValueError):
            continue
        if abs(qty) < 1e-9:
            continue

        try:
            price = _get_stock_price(symbol, date_str, price_cache)
        except FileNotFoundError:
            missing_symbols.append(symbol)
            continue

        if price is None:
            missing_symbols.append(symbol)
            continue

        total_asset += qty * price

    percent_change = (
        (total_asset - initial_cash) / initial_cash * 100 if initial_cash else 0.0
    )

    return FinalAssetRecord(
        base_model=base_model,
        operation=operation,
        value=total_asset,
        initial_cash=initial_cash,
        percent_change=percent_change,
        missing_symbols=missing_symbols,
        source_path=position_path,
    )


def gather_assets() -> Dict[str, Dict[str, FinalAssetRecord]]:
    price_cache: Dict[str, Dict[str, float]] = {}
    results: Dict[str, Dict[str, FinalAssetRecord]] = {}

    for base_model, operations in MODEL_SOURCES.items():
        base_results: Dict[str, FinalAssetRecord] = {}
        for operation in DEFAULT_OPERATIONS:
            path_str = (operations.get(operation, "") or "").strip()
            if not path_str:
                record = FinalAssetRecord(
                    base_model=base_model,
                    operation=operation,
                    value=PLACEHOLDER_ASSET_VALUE,
                    initial_cash=INITIAL_CASH_FALLBACK,
                    percent_change=0.0,
                    missing_symbols=[],
                    source_path=None,
                )
                base_results[operation] = record
                continue

            position_path = Path(path_str)
            if not position_path.is_absolute():
                position_path = (PROJECT_ROOT / path_str).resolve()

            if not position_path.exists():
                print(
                    f"[Warning] Position file not found: {position_path} ({base_model} / {operation}), using placeholder value {PLACEHOLDER_ASSET_VALUE}"
                )
                record = FinalAssetRecord(
                    base_model=base_model,
                    operation=operation,
                    value=PLACEHOLDER_ASSET_VALUE,
                    initial_cash=INITIAL_CASH_FALLBACK,
                    percent_change=0.0,
                    missing_symbols=[],
                    source_path=position_path,
                )
                base_results[operation] = record
                continue

            record = _compute_final_asset(
                base_model,
                operation,
                position_path,
                price_cache,
            )
            base_results[operation] = record

            if record.missing_symbols:
                print(
                    f"[Warning] {base_model} / {operation} has missing stock prices, ignoring: "
                    f"{', '.join(record.missing_symbols)}"
                )

        results[base_model] = base_results

    return results


def plot_bars(
    assets: Dict[str, Dict[str, FinalAssetRecord]],
    output_path: Path,
    title: str,
    annotate: bool = True,
    baseline_value: float | None = None,
) -> None:
    bases = [base for base in DEFAULT_BASE_MODELS if assets.get(base)]
    if not bases:
        raise ValueError("No base models found for plotting.")

    operations = DEFAULT_OPERATIONS
    num_ops = len(operations)

    group_spacing = 1.3
    x = np.arange(len(bases)) * group_spacing
    group_width = 0.8
    bar_width = min(group_width / max(num_ops, 1), 0.35)
    offsets = np.linspace(-(num_ops - 1) / 2, (num_ops - 1) / 2, num_ops) * bar_width * 1.05

    fig, ax = plt.subplots(figsize=(1.8 * len(bases) + 2.5, 6))
    all_values: List[float] = []

    for idx, operation in enumerate(operations):
        values = [assets[base][operation].value for base in bases]
        all_values.extend(values)
        bars = ax.bar(
            x + offsets[idx],
            values,
            bar_width,
            label=operation,
            color=COLORS[idx % len(COLORS)],
        )

        if annotate:
            for bar, base in zip(bars, bases):
                record = assets[base][operation]
                if record.percent_change >= 0:
                    label = f"+{record.percent_change:.1f}%"
                    label_color = "#b91c1c"
                else:
                    label = f"{record.percent_change:.1f}%"
                    label_color = "#16a34a"
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    label,
                    ha="center",
                    va="bottom",
                    fontsize=12,
                    color=label_color,
                    fontweight="bold",
                )

    ax.set_xticks(x)
    ax.set_xticklabels([base.upper() for base in bases], fontsize=12)
    ax.set_ylabel("Final total asset", fontsize=12)
    if baseline_value is not None:
        ax.axhline(
            baseline_value,
            color="#eab308",
            linestyle="--",
            linewidth=3,
            label="baseline",
            alpha=0.9,
        )
        ax.text(
            0.00,
            baseline_value,
            f"{baseline_value:,.0f}",
            va="bottom",
            ha="left",
            transform=ax.get_yaxis_transform(),
            fontsize=11,
            color="#b45309",
            fontweight="bold",
        )

    ax.set_title(title, fontsize=14, fontweight="bold")
    legend = ax.legend(title="Operation / Strategy")
    if legend:
        legend.get_title().set_fontsize(12)
        for text in legend.get_texts():
            text.set_fontsize(11)
    ax.grid(axis="y", linestyle="--", alpha=0.25)

    finite_values = [v for v in all_values if np.isfinite(v)]
    if finite_values:
        min_val = min(finite_values)
        max_val = max(finite_values)
        if max_val > min_val:
            span = max_val - min_val
            padding = max(span * 0.12, 80)
            lower_candidate = min_val - padding
            if lower_candidate < 0 and min_val > 0:
                lower = 0.0
            else:
                lower = lower_candidate
            upper = max_val + padding
            ax.set_ylim(lower, upper)
        else:
            ax.set_ylim(min_val - 100, max_val + 100)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    print(f"Bar chart saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read position records from agent_data and calculate final portfolio values, then plot bar charts."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output image path",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="Final Portfolio Value Comparison",
        help="Chart title",
    )
    parser.add_argument(
        "--no-annotate",
        action="store_true",
        help="Disable percentage change annotations on bar tops",
    )
    parser.add_argument(
        "--baseline",
        type=int,
        default=5265,
        help="Reference baseline asset value (draw horizontal line), set to 0 to disable",
    )
    args = parser.parse_args()

    assets = gather_assets()
    plot_bars(
        assets,
        args.output_path,
        args.title,
        annotate=not args.no_annotate,
        baseline_value=args.baseline,
    )


if __name__ == "__main__":
    main()


