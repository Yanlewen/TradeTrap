import os
import time
import json

import requests
from dotenv import load_dotenv

load_dotenv()

all_nasdaq_100_symbols = [
    "NVDA",
    "MSFT",
    "AAPL",
    "GOOG",
    "GOOGL",
    "AMZN",
    "META",
    "AVGO",
    "TSLA",
    "NFLX",
    "PLTR",
    "COST",
    "ASML",
    "AMD",
    "CSCO",
    "AZN",
    "TMUS",
    "MU",
    "LIN",
    "PEP",
    "SHOP",
    "APP",
    "INTU",
    "AMAT",
    "LRCX",
    "PDD",
    "QCOM",
    "ARM",
    "INTC",
    "BKNG",
    "AMGN",
    "TXN",
    "ISRG",
    "GILD",
    "KLAC",
    "PANW",
    "ADBE",
    "HON",
    "CRWD",
    "CEG",
    "ADI",
    "ADP",
    "DASH",
    "CMCSA",
    "VRTX",
    "MELI",
    "SBUX",
    "CDNS",
    "ORLY",
    "SNPS",
    "MSTR",
    "MDLZ",
    "ABNB",
    "MRVL",
    "CTAS",
    "TRI",
    "MAR",
    "MNST",
    "CSX",
    "ADSK",
    "PYPL",
    "FTNT",
    "AEP",
    "WDAY",
    "REGN",
    "ROP",
    "NXPI",
    "DDOG",
    "AXON",
    "ROST",
    "IDXX",
    "EA",
    "PCAR",
    "FAST",
    "EXC",
    "TTWO",
    "XEL",
    "ZS",
    "PAYX",
    "WBD",
    "BKR",
    "CPRT",
    "CCEP",
    "FANG",
    "TEAM",
    "CHTR",
    "KDP",
    "MCHP",
    "GEHC",
    "VRSK",
    "CTSH",
    "CSGP",
    "KHC",
    "ODFL",
    "DXCM",
    "TTD",
    "ON",
    "BIIB",
    "LULU",
    "CDW",
    "GFS",
]


def update_json(data: dict, SYMBOL: str, target_dir: str = None):
    # 如果没有指定目录，使用当前脚本所在目录（data/）
    if target_dir is None:
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = script_dir
    else:
        # 如果是相对路径，相对于脚本目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isabs(target_dir):
            target_dir = os.path.join(script_dir, target_dir)
    
    # 确保目标目录存在
    os.makedirs(target_dir, exist_ok=True)
    
    # 保存到 daily_prices_{SYMBOL}.json（与现有文件格式一致，在 data/ 目录）
    file_path = os.path.join(target_dir, f'daily_prices_{SYMBOL}.json')
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            # 合并新旧的"Time Series (60min)"
            old_ts = old_data.get("Time Series (60min)", {})
            new_ts = data.get("Time Series (60min)", {})
            # 合并：先添加旧数据，然后用新数据覆盖相同的时间戳（新数据优先）
            merged_ts = {**old_ts, **new_ts}
            
            print(f"  合并前：旧数据 {len(old_ts)} 条，新数据 {len(new_ts)} 条")
            print(f"  合并后：总计 {len(merged_ts)} 条数据")
            
            # 创建新的数据字典，避免直接修改传入的data
            merged_data = data.copy()
            merged_data["Time Series (60min)"] = merged_ts
            
            # 如果新数据没有Meta Data，保留旧的Meta Data
            if "Meta Data" not in merged_data and "Meta Data" in old_data:
                merged_data["Meta Data"] = old_data["Meta Data"]
            # 更新 Last Refreshed 为最新的
            if "Meta Data" in merged_data and "Meta Data" in old_data:
                # 保留新数据的 Last Refreshed（如果新数据更新）
                if "3. Last Refreshed" in data.get("Meta Data", {}):
                    merged_data["Meta Data"]["3. Last Refreshed"] = data["Meta Data"]["3. Last Refreshed"]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=4)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"✓ {SYMBOL} 数据已保存到 {file_path}")
                    
    except (IOError, json.JSONDecodeError, KeyError) as e:
        print(f"✗ 更新 {SYMBOL} 时出错: {e}")
        raise
         




def has_month_data(SYMBOL: str, month: str = "2025-09", target_dir: str = None) -> bool:
    """
    检查本地 daily_prices_{SYMBOL}.json 是否已经包含指定月份的数据
    通过判断 "Time Series (60min)" 里的时间戳是否以 month(YYYY-MM) 开头
    """
    # 与 update_json 中的路径逻辑保持一致
    if target_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = script_dir
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isabs(target_dir):
            target_dir = os.path.join(script_dir, target_dir)

    file_path = os.path.join(target_dir, f"daily_prices_{SYMBOL}.json")

    if not os.path.exists(file_path):
        # 根本没有文件，肯定没有该月数据
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts = data.get("Time Series (60min)", {})
        # 只要有任意一个时间戳是该月份的，就认为已经有该月的数据
        for timestamp in ts.keys():
            if str(timestamp).startswith(month):
                return True
        return False
    except (IOError, json.JSONDecodeError, KeyError):
        # 读文件有问题时，保守起见当作没有数据，后面重新拉取
        return False


def get_hourly_price(SYMBOL: str, month: str = "2025-09"):
    """
    获取指定股票指定月份的小时数据
    
    Args:
        SYMBOL: 股票代码
        month: 月份，格式为 YYYY-MM，例如 "2025-09"
    """
    FUNCTION = "TIME_SERIES_INTRADAY"
    INTERVAL = "60min"
    OUTPUTSIZE = 'compact'  # 高级会员可以使用 full
    APIKEY = os.getenv("ALPHAADVANTAGE_API_KEY")
    
    # 移除 entitlement 参数，这个参数可能导致权限问题
    # 高级会员账号应该默认有正确的权限
    url = f'https://www.alphavantage.co/query?function={FUNCTION}&symbol={SYMBOL}&interval={INTERVAL}&month={month}&outputsize={OUTPUTSIZE}&extended_hours=false&apikey={APIKEY}'
    
    print(f"正在获取 {SYMBOL} 的 {month} 小时数据...")
    
    try:
        r = requests.get(url, timeout=30)
        data = r.json()
        
        # 检查是否有错误信息
        if data.get("Note") is not None:
            print(f"✗ API 调用频率限制: {data.get('Note')}")
            return False
        
        if data.get("Information") is not None:
            print(f"✗ API 信息: {data.get('Information')}")
            return False
            
        if data.get("Error Message") is not None:
            print(f"✗ API 错误: {data.get('Error Message')}")
            return False
        
        # 检查是否有数据
        if "Time Series (60min)" not in data:
            print(f"✗ {SYMBOL} 没有返回时间序列数据")
            print(f"响应内容: {data}")
            return False
        
        # 保存数据
        update_json(data, SYMBOL)
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求 {SYMBOL} 数据时出错: {e}")
        return False
    except Exception as e:
        print(f"✗ 处理 {SYMBOL} 数据时出错: {e}")
        return False


if __name__ == "__main__":
    # 要检查/获取的目标月份
    target_month = "2025-09"

    print(f"开始检查并获取 Nasdaq 100 股票在 {target_month} 的小时数据")
    print("=" * 60)

    for symbol in all_nasdaq_100_symbols:
        print(f"\n--- {symbol} ---")
        # 先检查本地是否已有该月份数据
        if has_month_data(symbol, target_month):
            print(f"✓ {symbol} 已存在 {target_month} 的小时数据，跳过 API 调用")
            continue

        print(f"→ {symbol} 缺少 {target_month} 数据，调用 API 获取...")
        success = get_hourly_price(symbol, month=target_month)

        if success:
            print(f"✓ {symbol} 的 {target_month} 数据获取并保存成功")
        else:
            print(f"✗ {symbol} 的 {target_month} 数据获取失败")

        # 为了避免触发 Alpha Vantage 频率限制，适当 sleep 一下
        # 如果你是高级会员且确定频率没问题，可以把这个时间调小
        time.sleep(15)
