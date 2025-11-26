import os
import json


def has_month_data(daily_file: str, month: str = "2025-09") -> bool:
    """检查 daily_prices_*.json 里是否已经包含指定月份的数据"""
    if not os.path.exists(daily_file):
        return False

    try:
        with open(daily_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError):
        # 读不出来就当没数据，后面用新的覆盖补一次
        return False

    ts = data.get("Time Series (60min)", {})
    for ts_key in ts.keys():
        # 时间戳形如 "2025-09-30 15:00:00"
        if str(ts_key).startswith(month):
            return True
    return False


def merge_september_from_folder(
    base_dir: str,
    september_dir: str = "september_2025_prices",
    month: str = "2025-09",
):
    """
    把 september_2025_prices 里的 9 月数据合并进 data 目录下的 daily_prices_*.json
    - 如果 daily 文件已经有该月数据：跳过
    - 如果没有：将 9 月的所有时间戳合并进去（不重复覆盖已有 key）
    """
    september_path = os.path.join(base_dir, september_dir)

    if not os.path.isdir(september_path):
        print(f"✗ 找不到目录: {september_path}")
        return

    files = [f for f in os.listdir(september_path) if f.endswith(".json")]
    print(f"在 {september_path} 中找到 {len(files)} 个小时数据文件")

    for filename in files:
        if not filename.startswith("hourly_prices_") or not filename.endswith(".json"):
            continue

        symbol = filename[len("hourly_prices_") : -len(".json")]
        hourly_file = os.path.join(september_path, filename)
        daily_file = os.path.join(base_dir, f"daily_prices_{symbol}.json")

        print(f"\n=== 处理 {symbol} ===")

        if has_month_data(daily_file, month=month):
            print(f"✓ {symbol} 的 daily 文件已包含 {month} 数据，跳过合并")
            continue

        if not os.path.exists(hourly_file):
            print(f"✗ 未找到 {symbol} 的 9 月小时数据文件: {hourly_file}")
            continue

        try:
            with open(hourly_file, "r", encoding="utf-8") as f:
                hourly_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"✗ 读取 {hourly_file} 出错: {e}")
            continue

        hourly_ts = hourly_data.get("Time Series (60min)", {})
        if not hourly_ts:
            print(f"✗ {symbol} 的 9 月小时数据为空，跳过")
            continue

        # 只挑出 9 月份的时间戳（以 month 开头）
        september_ts = {
            k: v for k, v in hourly_ts.items() if str(k).startswith(month)
        }
        if not september_ts:
            print(f"✗ {symbol} 的小时数据中没有 {month} 的时间戳，跳过")
            continue

        # 如果 daily 文件不存在，就直接以 hourly_data 为基础新建一个
        if not os.path.exists(daily_file):
            print(f"→ {symbol} 没有 daily 文件，新建并写入 {month} 数据")
            new_data = {
                "Meta Data": hourly_data.get("Meta Data", {}),
                "Time Series (60min)": september_ts,
            }
            with open(daily_file, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)
            print(f"✓ 已创建 {daily_file} 并写入 {len(september_ts)} 条记录")
            continue

        # 否则：在已有 daily 文件上合并
        try:
            with open(daily_file, "r", encoding="utf-8") as f:
                daily_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"✗ 读取 {daily_file} 出错: {e}，跳过该标的")
            continue

        daily_ts = daily_data.get("Time Series (60min)", {})

        before_count = len(daily_ts)
        # 只补充不存在的 key（避免覆盖原有重复时间戳）
        for k, v in september_ts.items():
            if k not in daily_ts:
                daily_ts[k] = v
        after_count = len(daily_ts)

        daily_data["Time Series (60min)"] = daily_ts

        # Meta Data：优先保留原来的，如果没有就用 hourly 的
        if "Meta Data" not in daily_data and "Meta Data" in hourly_data:
            daily_data["Meta Data"] = hourly_data["Meta Data"]

        with open(daily_file, "w", encoding="utf-8") as f:
            json.dump(daily_data, f, ensure_ascii=False, indent=4)

        added = after_count - before_count
        print(
            f"→ {symbol} 合并 {month} 数据完成：新增 {added} 条记录（合并前 {before_count}, 合并后 {after_count}）"
        )


if __name__ == "__main__":
    # 当前脚本所在目录就是 data 目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    merge_september_from_folder(base_dir)


