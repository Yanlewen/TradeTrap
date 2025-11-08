#!/usr/bin/env python3
"""
预处理Agent数据，生成JSON文件供前端展示
"""
import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import glob

# 数据目录
DATA_DIR = Path("../data/agent_data")
PRICE_DIR = Path("../data")
OUTPUT_DIR = Path("data")

# Agent列表
AGENTS = [
    "deepseek-v3-whole-month",
    "deepseek-v3-whole-month-with-x-and-reddit-1105"
    "deepseek-v3-ReverseExpectations-injection-month",
    "deepseek-v3-fakenews-50%-month"
]

def load_jsonl(file_path):
    """加载JSONL文件"""
    data = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return data

def load_price_data(symbol, price_cache):
    """加载股票价格数据"""
    if symbol in price_cache:
        return price_cache[symbol]
    
    price_file = PRICE_DIR / f"daily_prices_{symbol}.json"
    if not price_file.exists():
        price_cache[symbol] = {}
        return {}
    
    try:
        with open(price_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            prices = {}
            
            # 尝试不同的格式
            if 'Time Series (60min)' in data:
                time_series = data['Time Series (60min)']
                for timestamp, values in time_series.items():
                    close_price = float(values.get('4. close', 0))
                    prices[timestamp] = close_price
            elif 'Time Series (Daily)' in data:
                time_series = data['Time Series (Daily)']
                for timestamp, values in time_series.items():
                    close_price = float(values.get('4. close', 0))
                    prices[timestamp] = close_price
            elif isinstance(data, dict):
                # 尝试直接是时间戳字典
                for k, v in data.items():
                    if isinstance(v, (int, float)):
                        prices[k] = float(v)
                    elif isinstance(v, dict) and 'close' in v:
                        prices[k] = float(v['close'])
            
            price_cache[symbol] = prices
            return prices
    except Exception as e:
        print(f"  警告: 加载价格数据失败 {symbol}: {e}")
        price_cache[symbol] = {}
        return {}

def get_stock_price(symbol, date_str, price_cache):
    """获取指定日期时间的股票价格"""
    prices = load_price_data(symbol, price_cache)
    if not prices:
        return 0.0
    
    # 尝试精确匹配
    if date_str in prices:
        return prices[date_str]
    
    # 尝试匹配相同日期不同时间
    date_part = date_str.split(' ')[0]
    matching_prices = {k: v for k, v in prices.items() if k.startswith(date_part)}
    if matching_prices:
        sorted_keys = sorted(matching_prices.keys())
        return matching_prices[sorted_keys[-1]]
    
    # 如果没有找到，尝试前一个日期
    matching_prices = {k: v for k, v in prices.items() if date_part in k}
    if matching_prices:
        sorted_keys = sorted(matching_prices.keys())
        return matching_prices[sorted_keys[-1]]
    
    return 0.0

def calculate_total_asset(position, price_cache, initial_cash=5000.0):
    """计算总资产：现金 + 持仓股票市值"""
    if not position or 'positions' not in position:
        return initial_cash
    
    cash = position['positions'].get('CASH', initial_cash)
    total_stock_value = 0.0
    
    # 计算持仓股票市值
    for symbol, quantity in position['positions'].items():
        if symbol != 'CASH' and quantity > 0:
            price = get_stock_price(symbol, position['date'], price_cache)
            total_stock_value += price * quantity
    
    return cash + total_stock_value

def process_agent_data(agent_name, price_cache):
    """处理单个agent的数据"""
    agent_dir = DATA_DIR / agent_name
    
    # 处理position数据
    position_file = agent_dir / "position" / "position.jsonl"
    positions_data = load_jsonl(position_file)
    
    # 按日期组织position数据，并计算总资产
    positions_by_date = {}
    initial_cash = 5000.0
    for pos in positions_data:
        date = pos.get('date', '')
        if date:
            # 计算总资产
            total_asset = calculate_total_asset(pos, price_cache, initial_cash)
            pos['total_asset'] = total_asset
            positions_by_date[date] = pos
            # 更新initial_cash（使用第一个位置）
            if not positions_by_date or initial_cash == 5000.0:
                initial_cash = pos.get('positions', {}).get('CASH', 5000.0)
    
    # 处理log数据
    log_dir = agent_dir / "log"
    log_files = glob.glob(str(log_dir / "**" / "log.jsonl"), recursive=True)
    
    # 按日期组织log数据
    logs_by_date = defaultdict(list)
    dates = set()
    
    for log_file in log_files:
        parts = Path(log_file).parts
        if len(parts) >= 2:
            date_str = parts[-2]
            dates.add(date_str)
            
            logs = load_jsonl(log_file)
            logs_by_date[date_str].extend(logs)
    
    # 计算最终总资产
    final_total_asset = initial_cash
    if positions_data:
        last_pos = positions_data[-1]
        final_total_asset = last_pos.get('total_asset', initial_cash)
    
    # 合并数据
    result = {
        'agent_name': agent_name,
        'dates': sorted(list(dates)),
        'positions': positions_by_date,
        'logs': dict(logs_by_date),
        'summary': {
            'total_dates': len(dates),
            'initial_cash': initial_cash,
            'final_total_asset': final_total_asset
        }
    }
    
    return result

def main():
    """主函数"""
    print("开始预处理数据...")
    print("加载股票价格数据（首次运行可能较慢）...")
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # 价格缓存
    price_cache = {}
    
    all_data = {}
    
    # 处理每个agent
    for agent in AGENTS:
        print(f"\n处理 {agent}...")
        try:
            data = process_agent_data(agent, price_cache)
            all_data[agent] = data
            print(f"  - 日期数量: {data['summary']['total_dates']}")
            print(f"  - 初始现金: ${data['summary']['initial_cash']:.2f}")
            print(f"  - 最终总资产: ${data['summary']['final_total_asset']:.2f}")
        except Exception as e:
            print(f"处理 {agent} 时出错: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 保存为JSON文件
    output_file = OUTPUT_DIR / "agents_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n数据已保存到 {output_file}")
    print(f"处理了 {len(all_data)} 个agent")
    print(f"加载了 {len(price_cache)} 个股票的价格数据")

if __name__ == "__main__":
    main()
