"""根据真实 agent 数据生成带局部放大的收益曲线图。

脚本读取 `agent_viewer/data/agents_data.json` 中的累计资产数据，
对指定的两名 agent（默认：baseline 与带 Reddit/X 信号的版本）
生成整体曲线 + 局部放大图，同时绘制波动区间阴影。

运行方式：
    python scripts/plot_zoom_inset.py

输出：
    默认写入项目根目录下 `assets/returns_zoom_inset.png`
"""

from __future__ import annotations

import json
import pathlib
from typing import Dict

import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS_DATA_PATH = PROJECT_ROOT / "agent_viewer" / "data" / "agents_data.json"
OUTPUT_IMAGE_PATH = PROJECT_ROOT / "assets" / "returns_zoom_inset.png"

# 默认对比的两个 agent，按需修改
DEFAULT_PURPLE_AGENT = "deepseek-v3-whole-month"
DEFAULT_ORANGE_AGENT = "deepseek-v3-whole-month-with-x-and-reddit-1105"



def configure_chinese_font() -> None:
    """尝试自动选择可用的中文字体，避免中文字符显示为方块。"""

    preferred_fonts = [
        "SimHei",
        "Microsoft YaHei",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
        "PingFang SC",
        "Source Han Sans SC",
        "HarmonyOS Sans SC",
    ]

    available = {font.name for font in fm.fontManager.ttflist}

    for name in preferred_fonts:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            break
    else:
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]

    plt.rcParams["axes.unicode_minus"] = False


configure_chinese_font()


def load_agents_data(json_path: pathlib.Path = AGENTS_DATA_PATH) -> Dict[str, dict]:
    """加载 agents_data.json."""

    json_path = json_path.resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"未找到 agents_data.json: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("agents_data.json 内容格式异常，期望为字典")

    return data


def agent_to_dataframe(agents_data: Dict[str, dict], agent_name: str) -> pd.DataFrame:
    """提取单个 agent 的累计资产数据并转换为 DataFrame."""

    if agent_name not in agents_data:
        available = ", ".join(sorted(agents_data))
        raise KeyError(f"agents_data.json 中没有 {agent_name}，可选项: {available}")

    payload = agents_data[agent_name]
    positions = payload.get("positions", {})
    if not positions:
        raise ValueError(f"agent {agent_name} 不包含 position 数据")

    records = []
    for ts_str, info in positions.items():
        timestamp = pd.to_datetime(ts_str)
        total_asset = float(info.get("total_asset", 0.0))
        cash = float(info.get("positions", {}).get("CASH", 0.0))
        records.append(
            {
                "timestamp": timestamp,
                "total_asset": total_asset,
                "cash": cash,
            }
        )

    df = (
        pd.DataFrame(records)
        .sort_values("timestamp")
        .drop_duplicates("timestamp", keep="last")
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError(f"agent {agent_name} 没有可用的时间序列数据")

    base_asset = df["total_asset"].iloc[0]
    if base_asset == 0:
        raise ValueError(f"agent {agent_name} 的首个 total_asset 为 0，无法计算收益率")

    df["cum_return_pct"] = (df["total_asset"] / base_asset - 1.0) * 100

    # 使用指数加权与滑动窗口结合，构造平滑的阴影带宽度
    ewm_std = df["cum_return_pct"].ewm(span=6, adjust=False).std()
    roll_std = df["cum_return_pct"].rolling(window=4, min_periods=1).std()
    df["ci"] = (ewm_std.fillna(0) + roll_std.fillna(0)) / 2
    df["ci"] = df["ci"].fillna(0)

    return df


def compose_plot_dataframe(df_orange: pd.DataFrame, df_purple: pd.DataFrame) -> pd.DataFrame:
    """对齐两条时间序列，生成绘图所需的 DataFrame."""

    timeline = pd.DatetimeIndex(
        sorted(set(df_orange["timestamp"]) | set(df_purple["timestamp"]))
    )

    orange = (
        df_orange.set_index("timestamp")
        .reindex(timeline)
        .interpolate(method="time")
        .ffill()
        .bfill()
    )

    purple = (
        df_purple.set_index("timestamp")
        .reindex(timeline)
        .interpolate(method="time")
        .ffill()
        .bfill()
    )

    merged = pd.DataFrame(
        {
            "timestamp": timeline,
            "strategy_orange": orange["cum_return_pct"].to_numpy(),
            "orange_ci": orange["ci"].to_numpy(),
            "strategy_purple": purple["cum_return_pct"].to_numpy(),
            "purple_ci": purple["ci"].to_numpy(),
            "orange_asset": orange["total_asset"].to_numpy(),
            "purple_asset": purple["total_asset"].to_numpy(),
        }
    )

    return merged


def _nearest_row(df: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    """获取与 ts 最近的行（假设 df 的 timestamp 已排序）。"""

    idx = pd.Index(df["timestamp"])  # 确保为 Index 对象
    position = idx.get_indexer([ts], method="nearest")[0]
    position = max(0, min(position, len(df) - 1))
    return df.iloc[position]


def plot_zoom_inset(
    df: pd.DataFrame,
    highlight_start: str | pd.Timestamp,
    highlight_end: str | pd.Timestamp | None = None,
    output_path: pathlib.Path | None = None,
    orange_label: str = "策略A",
    purple_label: str = "策略B",
    title: str = "收益曲线对比（含局部放大）",
) -> pathlib.Path:
    """绘制主图 + 局部放大子图，带阴影置信区间。"""

    df = df.sort_values("timestamp").reset_index(drop=True)
    if df.empty:
        raise ValueError("输入数据为空，无法绘图")

    highlight_start = pd.to_datetime(highlight_start)
    if highlight_end is None:
        highlight_end = highlight_start + pd.Timedelta(days=2)
    highlight_end = pd.to_datetime(highlight_end)

    if highlight_start < df["timestamp"].min() or highlight_start > df["timestamp"].max():
        raise ValueError("highlight_start 超出数据范围")
    if highlight_end <= highlight_start:
        raise ValueError("highlight_end 必须晚于 highlight_start")

    mask_zoom = (df["timestamp"] >= highlight_start) & (df["timestamp"] <= highlight_end)
    df_zoom = df.loc[mask_zoom]
    if df_zoom.empty:
        raise ValueError("局部放大区间没有数据，请调整 highlight_start / highlight_end")

    orange = "#ff8c42"
    orange_light = "#ff8c4233"
    purple = "#6a5acd"
    purple_light = "#6a5acd33"

    fig, ax_purple = plt.subplots(figsize=(14, 6), dpi=300, constrained_layout=False)
    ax_orange = ax_purple.twinx()

    # 主图：紫色（基准）
    ax_purple.plot(
        df["timestamp"],
        df["strategy_purple"],
        color=purple,
        linewidth=2.2,
        label=purple_label,
    )
    ax_purple.fill_between(
        df["timestamp"],
        df["strategy_purple"] - df["purple_ci"],
        df["strategy_purple"] + df["purple_ci"],
        color=purple_light,
        linewidth=0,
        alpha=0.6,
    )

    # 主图：橙色（对比策略）
    ax_orange.plot(
        df["timestamp"],
        df["strategy_orange"],
        color=orange,
        linewidth=2.2,
        label=orange_label,
    )
    ax_orange.fill_between(
        df["timestamp"],
        df["strategy_orange"] - df["orange_ci"],
        df["strategy_orange"] + df["orange_ci"],
        color=orange_light,
        linewidth=0,
        alpha=0.6,
    )

    ax_purple.axvspan(highlight_start, highlight_end, color="#0000000f", zorder=-1)

    ax_purple.set_title(title, fontsize=18, pad=16)
    ax_purple.set_xlabel("时间")
    ax_purple.set_ylabel(f"{purple_label} 累计收益率(%)", color=purple)
    ax_orange.set_ylabel(f"{orange_label} 累计收益率(%)", color=orange)

    ax_purple.tick_params(axis="y", colors=purple)
    ax_orange.tick_params(axis="y", colors=orange)

    ax_purple.grid(alpha=0.2, linestyle="--")
    ax_orange.grid(False)

    # X 轴日期格式
    ax_purple.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))
    ax_purple.tick_params(axis="x", rotation=0)

    # 合并图例
    handles_purple, labels_purple = ax_purple.get_legend_handles_labels()
    handles_orange, labels_orange = ax_orange.get_legend_handles_labels()
    ax_purple.legend(
        handles_purple + handles_orange,
        labels_purple + labels_orange,
        loc="upper left",
        frameon=False,
    )

    # 局部放大
    ax_inset = ax_purple.inset_axes([0.05, 0.45, 0.48, 0.48])
    ax_inset_orange = ax_inset.twinx()

    ax_inset.plot(
        df_zoom["timestamp"],
        df_zoom["strategy_purple"],
        color=purple,
        linewidth=2.0,
    )
    ax_inset.fill_between(
        df_zoom["timestamp"],
        df_zoom["strategy_purple"] - df_zoom["purple_ci"],
        df_zoom["strategy_purple"] + df_zoom["purple_ci"],
        color=purple_light,
        linewidth=0,
        alpha=0.7,
    )

    ax_inset_orange.plot(
        df_zoom["timestamp"],
        df_zoom["strategy_orange"],
        color=orange,
        linewidth=2.0,
    )
    ax_inset_orange.fill_between(
        df_zoom["timestamp"],
        df_zoom["strategy_orange"] - df_zoom["orange_ci"],
        df_zoom["strategy_orange"] + df_zoom["orange_ci"],
        color=orange_light,
        linewidth=0,
        alpha=0.7,
    )

    ax_inset.set_xlim(highlight_start, highlight_end)
    ax_inset.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax_inset.tick_params(axis="x", rotation=45, labelsize=8)
    ax_inset.tick_params(axis="y", labelsize=8, colors=purple)
    ax_inset_orange.tick_params(axis="y", labelsize=8, colors=orange)

    ax_inset.grid(alpha=0.2, linestyle=":")
    ax_inset_orange.grid(False)
    ax_inset.set_facecolor("#ffffffcc")

    ax_purple.indicate_inset_zoom(ax_inset, edgecolor="black", linestyle="--", lw=0.8)

    # 标注分化点（使用离 highlight_start 最近的时间点）
    nearest = _nearest_row(df_zoom, highlight_start)
    ax_inset_orange.annotate(
        "策略分化",
        xy=(nearest["timestamp"], nearest["strategy_orange"]),
        xytext=(nearest["timestamp"] + pd.Timedelta(hours=2), nearest["strategy_orange"] + 1.5),
        arrowprops=dict(arrowstyle="->", color=orange, lw=1.2),
        fontsize=9,
        color=orange,
    )
    ax_inset.annotate(
        "基准走势",
        xy=(nearest["timestamp"], nearest["strategy_purple"]),
        xytext=(nearest["timestamp"] + pd.Timedelta(hours=2), nearest["strategy_purple"] - 1.5),
        arrowprops=dict(arrowstyle="->", color=purple, lw=1.2),
        fontsize=9,
        color=purple,
    )

    fig.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.12)

    if output_path is None:
        output_path = OUTPUT_IMAGE_PATH
    else:
        output_path = pathlib.Path(output_path).resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)

    return output_path


def main() -> None:
    agents_data = load_agents_data()

    df_orange = agent_to_dataframe(agents_data, DEFAULT_ORANGE_AGENT)
    df_purple = agent_to_dataframe(agents_data, DEFAULT_PURPLE_AGENT)

    plot_df = compose_plot_dataframe(df_orange, df_purple)

    highlight_start = pd.Timestamp("2025-10-03 14:00:00")
    highlight_end = pd.Timestamp("2025-10-07 15:00:00")

    output = plot_zoom_inset(
        plot_df,
        highlight_start=highlight_start,
        highlight_end=highlight_end,
        orange_label=DEFAULT_ORANGE_AGENT,
        purple_label=DEFAULT_PURPLE_AGENT,
        title="Agent 收益对比（含局部放大）",
        output_path=OUTPUT_IMAGE_PATH,
    )

    print(f"图表已保存至: {output}")


if __name__ == "__main__":
    main()


