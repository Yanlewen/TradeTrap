import glob
import json
import os

sse_50_codes = [
    "600519.SHH",
    "601318.SHH",
    "600036.SHH",
    "601899.SHH",
    "600900.SHH",
    "601166.SHH",
    "600276.SHH",
    "600030.SHH",
    "603259.SHH",
    "688981.SHH",
    "688256.SHH",
    "601398.SHH",
    "688041.SHH",
    "601211.SHH",
    "601288.SHH",
    "601328.SHH",
    "688008.SHH",
    "600887.SHH",
    "600150.SHH",
    "601816.SHH",
    "601127.SHH",
    "600031.SHH",
    "688012.SHH",
    "603501.SHH",
    "601088.SHH",
    "600309.SHH",
    "601601.SHH",
    "601668.SHH",
    "603993.SHH",
    "601012.SHH",
    "601728.SHH",
    "600690.SHH",
    "600809.SHH",
    "600941.SHH",
    "600406.SHH",
    "601857.SHH",
    "601766.SHH",
    "601919.SHH",
    "600050.SHH",
    "600760.SHH",
    "601225.SHH",
    "600028.SHH",
    "601988.SHH",
    "688111.SHH",
    "601985.SHH",
    "601888.SHH",
    "601628.SHH",
    "601600.SHH",
    "601658.SHH",
    "600048.SHH"
]

# 合并所有以 daily_price 开头的 json，逐文件一行写入 merged.jsonl
current_dir = os.path.dirname(__file__)
pattern = os.path.join(current_dir, "A_stock_data/daily_price*.json")
files = sorted(glob.glob(pattern))

output_file = os.path.join(current_dir, "merged.jsonl")

with open(output_file, "w", encoding="utf-8") as fout:
    for fp in files:
        basename = os.path.basename(fp)
        # 仅当文件名包含任一纳指100成分符号时才写入
        if not any(symbol in basename for symbol in sse_50_codes):
            continue
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 统一重命名："1. open" -> "1. buy price"；"4. close" -> "4. sell price"
        # 对于最新的一天，只保留并写入 "1. buy price"
        try:
            # 查找所有以 "Time Series" 开头的键
            series = None
            for key, value in data.items():
                if key.startswith("Time Series"):
                    series = value
                    break
            if isinstance(series, dict) and series:
                # 先对所有日期做键名重命名
                for d, bar in list(series.items()):
                    if not isinstance(bar, dict):
                        continue
                    if "1. open" in bar:
                        bar["1. buy price"] = bar.pop("1. open")
                    if "4. close" in bar:
                        bar["4. sell price"] = bar.pop("4. close")
                # 再处理最新日期，仅保留买入价
                latest_date = max(series.keys())
                latest_bar = series.get(latest_date, {})
                if isinstance(latest_bar, dict):
                    buy_val = latest_bar.get("1. buy price")
                    series[latest_date] = {"1. buy price": buy_val} if buy_val is not None else {}
                # 更新 Meta Data 描述
                meta = data.get("Meta Data", {})
                if isinstance(meta, dict):
                    meta["1. Information"] = "Daily Prices (buy price, high, low, sell price) and Volumes"
                    # 如果包含.SHH，替换成.SH
                    symbol = meta.get("2. Symbol", "")
                    # print("symbol: ", symbol)
                    symbol = symbol.replace(".SHH", ".SH")
                    # print("symbol: ", symbol)
                    meta["2. Symbol"] = symbol
        except Exception:
            # 若结构异常则原样写入
            pass

        fout.write(json.dumps(data, ensure_ascii=False) + "\n")
