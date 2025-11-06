"""Generate a带局部放大和阴影区间的收益对比图.

用途：对比两条收益曲线（例如橙色线代表策略A、紫色线代表策略B），
并重点放大某个时间窗口（如 10/03 14:00 之后）的走势细节。

运行方式：
    python scripts/plot_zoom_inset.py

输出：在项目根目录下生成 `assets/returns_zoom_inset.png` 图片。
"""

from __future__ import annotations

import pathlib

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _make_demo_data(seed: int = 7) -> pd.DataFrame:
    """构造示例数据，实际使用时可替换为真实收益序列读取逻辑。

    返回值包含：
        timestamp: 时间索引（5 分钟间隔）
        strategy_orange: 橙色曲线（例如叠加了策略调整后的收益）
        strategy_purple: 紫色曲线（例如基准策略收益）
        orange_ci: 橙色曲线的置信区间半宽，用于 fill_between 阴影
        purple_ci: 紫色曲线的置信区间半宽
    """

    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2022-10-01 09:30")
    periods = 600  # 约 2 天的 5 分钟级数据
    freq = "5min"

    timeline = pd.date_range(start=start, periods=periods, freq=freq)

    # 基础趋势
    base_trend = np.cumsum(rng.normal(0, 0.05, periods))
    strategy_purple = 1.5 + 0.02 * np.linspace(0, periods - 1, periods) + base_trend

    # 橙色策略在 10/03 14:00 之后做出不同操作，收益产生显著差异
    pivot = pd.Timestamp("2022-10-03 14:00")
    pivot_idx = int(np.clip(np.searchsorted(timeline, pivot), 0, periods - 1))

    strategy_orange = strategy_purple.copy()
    # 在 pivot 后引入超额收益和更高波动
    extra = np.zeros(periods)
    extra[pivot_idx:] = np.linspace(0, 3, periods - pivot_idx)
    extra[pivot_idx:] += np.cumsum(rng.normal(0.02, 0.08, periods - pivot_idx))
    strategy_orange += extra

    # 构造置信区间宽度
    orange_ci = 0.3 + 0.05 * rng.random(periods)
    purple_ci = 0.25 + 0.05 * rng.random(periods)

    return pd.DataFrame(
        {
            "timestamp": timeline,
            "strategy_orange": strategy_orange,
            "strategy_purple": strategy_purple,
            "orange_ci": orange_ci,
            "purple_ci": purple_ci,
        }
    )


def plot_zoom_inset(
    df: pd.DataFrame,
    highlight_start: str | pd.Timestamp,
    highlight_end: str | pd.Timestamp | None = None,
    output_path: pathlib.Path | None = None,
) -> pathlib.Path:
    """绘制主图 + 局部放大子图，带阴影置信区间。

    Args:
        df: 包含 timestamp、strategy_orange、strategy_purple、orange_ci、purple_ci 列的数据。
        highlight_start: 局部放大区域的起始时间。
        highlight_end: 局部放大区域的结束时间，缺省时默认使用 highlight_start 之后 6 小时。
        output_path: 输出图片路径；缺省写入 assets/returns_zoom_inset.png。

    Returns:
        输出图片的绝对路径。
    """

    df = df.sort_values("timestamp").reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    highlight_start = pd.to_datetime(highlight_start)
    if highlight_end is None:
        highlight_end = highlight_start + pd.Timedelta(hours=6)
    highlight_end = pd.to_datetime(highlight_end)

    mask_zoom = (df["timestamp"] >= highlight_start) & (
        df["timestamp"] <= highlight_end
    )
    df_zoom = df.loc[mask_zoom]
    if df_zoom.empty:
        raise ValueError("局部放大区间没有数据，请调整 highlight_start / highlight_end")

    # 配色
    orange = "#ff8c42"
    orange_light = "#ff8c4233"  # 带透明度的阴影
    purple = "#6a5acd"
    purple_light = "#6a5acd33"

    fig, ax_main = plt.subplots(figsize=(14, 6), dpi=300, constrained_layout=False)

    # 主图绘制
    ax_main.plot(
        df["timestamp"],
        df["strategy_purple"],
        color=purple,
        linewidth=2.2,
        label="紫色线：基准策略",
    )
    ax_main.fill_between(
        df["timestamp"],
        df["strategy_purple"] - df["purple_ci"],
        df["strategy_purple"] + df["purple_ci"],
        color=purple_light,
        linewidth=0,
        alpha=0.6,
    )

    ax_main.plot(
        df["timestamp"],
        df["strategy_orange"],
        color=orange,
        linewidth=2.2,
        label="橙色线：策略调整",
    )
    ax_main.fill_between(
        df["timestamp"],
        df["strategy_orange"] - df["orange_ci"],
        df["strategy_orange"] + df["orange_ci"],
        color=orange_light,
        linewidth=0,
        alpha=0.6,
    )

    # 高亮区域
    ax_main.axvspan(highlight_start, highlight_end, color="#0000000f", zorder=-1)

    ax_main.set_title("收益曲线对比（含局部放大）", fontsize=18, pad=16)
    ax_main.set_xlabel("时间")
    ax_main.set_ylabel("累计收益")
    ax_main.legend(loc="upper left", frameon=False)
    ax_main.grid(alpha=0.2, linestyle="--")

    # X 轴格式化为日期 + 时间
    ax_main.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))
    ax_main.tick_params(axis="x", rotation=0)

    ax_inset = ax_main.inset_axes([0.05, 0.45, 0.45, 0.45])
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
    ax_inset.plot(
        df_zoom["timestamp"],
        df_zoom["strategy_orange"],
        color=orange,
        linewidth=2.0,
    )
    ax_inset.fill_between(
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
    ax_inset.tick_params(axis="y", labelsize=8)
    ax_inset.grid(alpha=0.2, linestyle=":")
    ax_inset.set_facecolor("#ffffffcc")

    # 在主图上标记出局部放大区域边框 + 连接线
    ax_main.indicate_inset_zoom(ax_inset, edgecolor="black", linestyle="--", lw=0.8)

    # 标注差异点
    pivot_point = df.loc[df["timestamp"] == highlight_start]
    if not pivot_point.empty:
        y_orange = float(pivot_point["strategy_orange"].iloc[0])
        y_purple = float(pivot_point["strategy_purple"].iloc[0])
        ax_inset.annotate(
            "策略分化",
            xy=(highlight_start, y_orange),
            xytext=(highlight_start + pd.Timedelta(minutes=40), y_orange + 1.2),
            arrowprops=dict(arrowstyle="->", color=orange, lw=1.2),
            fontsize=9,
            color=orange,
        )
        ax_inset.annotate(
            "基准策略",
            xy=(highlight_start, y_purple),
            xytext=(highlight_start + pd.Timedelta(minutes=40), y_purple - 1.5),
            arrowprops=dict(arrowstyle="->", color=purple, lw=1.2),
            fontsize=9,
            color=purple,
        )

    fig.tight_layout(rect=(0.02, 0.02, 0.98, 0.98))

    if output_path is None:
        output_path = pathlib.Path(__file__).resolve().parents[1] / "assets" / "returns_zoom_inset.png"
    else:
        output_path = pathlib.Path(output_path).resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)

    return output_path


def main() -> None:
    # TODO: 若有真实数据，可在此处替换成 `pd.read_csv` / `read_parquet` 等读取逻辑。
    df = _make_demo_data()
    output = plot_zoom_inset(df, highlight_start="2022-10-03 14:00", highlight_end="2022-10-03 20:00")
    print(f"图表已保存至: {output}")


if __name__ == "__main__":
    main()


