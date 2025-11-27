#!/usr/bin/env python3
"""
计算交易Agent的量化指标
支持一次性处理多个position.jsonl文件
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import numpy as np

# ==================== 配置区域 ====================
# 在这里直接配置要处理的position文件路径和显示名称（支持多个文件）
# 方式1（推荐）: 使用字典列表，可以自定义每个文件在表格中的显示名称
POSITION_FILES = [
    {
        "name": "aitrader prompt injection",  # 表格中显示的名称
        "path": "data/agent_data/deepseek/deepseek-v3-ReverseExpectations-injection-month/position/position.jsonl"
    },
    {
        "name": "aitrader with news",
        "path": "data/agent_data/deepseek/deepseek-v3-whole-month-with-x-and-reddit-1105/position/position.jsonl"
    },
    {
        "name": "aitrader base",
        "path": "data/agent_data/deepseek/deepseek-v3-whole-month/position/position.jsonl"
    },
    {
        "name": "valuecell base",
        "path": "data/agent_data/valuecell-deepseek-v3-5k-whole-month-2/position/position.jsonl"
    },
    {
        "name": "valuecell prompt injection",
        "path": "data/agent_data/valuecell-deepseek-v3-5k-prompt-injection/position/position.jsonl"
    },

]

# 方式2: 也可以使用简单的字符串列表（自动从路径提取名称）
# POSITION_FILES = [
#     "data/agent_data/deepseek/deepseek-v3-memory-v3_memory_injection-positions0-day-attack-month-test17/position/position.jsonl",
#     "data/agent_data/deepseek/deepseek-v3-whole-month-with-x-and-reddit-1105/position/position.jsonl",
#     "data/agent_data/deepseek/deepseek-v3-whole-month/position/position.jsonl",
# ]
# ==================================================

# 价格数据目录
PRICE_DIR = Path(__file__).parent / "data"

# Entry/Exit Quality 的时间窗口（天数）
ENQ_WINDOWS = [1, 3, 5, 10]


class PriceCache:
    """价格数据缓存"""
    def __init__(self, price_dir: Path):
        self.price_dir = price_dir
        self.cache = {}
        self.high_low_cache = {}  # 存储high/low数据用于Entry/Exit Quality
    
    def load_price_data(self, symbol: str) -> Dict[str, float]:
        """加载股票收盘价数据"""
        if symbol in self.cache:
            return self.cache[symbol]
        
        price_file = self.price_dir / f"daily_prices_{symbol}.json"
        if not price_file.exists():
            self.cache[symbol] = {}
            return {}
        
        try:
            with open(price_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                prices = {}
                
                if 'Time Series (60min)' in data:
                    time_series = data['Time Series (60min)']
                    for timestamp, values in time_series.items():
                        close_price = float(values.get('4. close', 0))
                        if close_price > 0:
                            prices[timestamp] = close_price
                
                self.cache[symbol] = prices
                return prices
        except Exception as e:
            print(f"  警告: 加载价格数据失败 {symbol}: {e}", file=sys.stderr)
            self.cache[symbol] = {}
            return {}
    
    def load_high_low_data(self, symbol: str) -> Dict[str, Dict[str, float]]:
        """加载股票high/low数据用于Entry/Exit Quality计算"""
        if symbol in self.high_low_cache:
            return self.high_low_cache[symbol]
        
        price_file = self.price_dir / f"daily_prices_{symbol}.json"
        if not price_file.exists():
            self.high_low_cache[symbol] = {}
            return {}
        
        try:
            with open(price_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                prices = {}
                
                if 'Time Series (60min)' in data:
                    time_series = data['Time Series (60min)']
                    for timestamp, values in time_series.items():
                        high = float(values.get('2. high', 0))
                        low = float(values.get('3. low', 0))
                        if high > 0 and low > 0:
                            prices[timestamp] = {'high': high, 'low': low}
                
                self.high_low_cache[symbol] = prices
                return prices
        except Exception:
            self.high_low_cache[symbol] = {}
            return {}
    
    def get_price(self, symbol: str, date_str: str) -> float:
        """获取指定日期时间的股票价格"""
        prices = self.load_price_data(symbol)
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
        
        return 0.0
    
    def get_future_low(self, symbol: str, date_str: str, days: int) -> Optional[float]:
        """获取未来N天内的最低价（用于Entry Quality）"""
        high_low = self.load_high_low_data(symbol)
        if not high_low:
            return None
        
        # 解析日期
        try:
            base_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            # 计算目标日期（考虑交易日，假设每天6.5小时交易时间）
            target_date = base_date + timedelta(days=days)
        except:
            return None
        
        # 找到未来N天内的最低价
        min_low = None
        sorted_timestamps = sorted(high_low.keys())
        
        for timestamp in sorted_timestamps:
            try:
                ts_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                if ts_date > base_date and ts_date <= target_date:
                    low = high_low[timestamp].get('low', float('inf'))
                    if low != float('inf') and (min_low is None or low < min_low):
                        min_low = low
            except:
                continue
        
        return min_low if min_low and min_low != float('inf') else None
    
    def get_future_high(self, symbol: str, date_str: str, days: int) -> Optional[float]:
        """获取未来N天内的最高价（用于Exit Quality）"""
        high_low = self.load_high_low_data(symbol)
        if not high_low:
            return None
        
        # 解析日期
        try:
            base_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            # 计算目标日期
            target_date = base_date + timedelta(days=days)
        except:
            return None
        
        # 找到未来N天内的最高价
        max_high = None
        sorted_timestamps = sorted(high_low.keys())
        
        for timestamp in sorted_timestamps:
            try:
                ts_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                if ts_date > base_date and ts_date <= target_date:
                    high = high_low[timestamp].get('high', 0)
                    if high > 0 and (max_high is None or high > max_high):
                        max_high = high
            except:
                continue
        
        return max_high if max_high and max_high > 0 else None


class MetricsCalculator:
    """指标计算器"""
    def __init__(self, position_file: str, price_dir: Path):
        self.position_file = Path(position_file)
        self.price_cache = PriceCache(price_dir)
        self.positions_data = []
        self.initial_cash = 5000.0
        self.total_trading_hours = None  # 总交易时间点数
        self.load_positions()
    
    def load_positions(self):
        """加载position数据"""
        if not self.position_file.exists():
            raise FileNotFoundError(f"Position文件不存在: {self.position_file}")
        
        with open(self.position_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        self.positions_data.append(data)
                    except json.JSONDecodeError:
                        continue
        
        if self.positions_data:
            # 获取初始资金
            first_pos = self.positions_data[0].get('positions', {})
            self.initial_cash = first_pos.get('CASH', 5000.0)
            # 计算总交易时间点数
            self.calculate_total_trading_hours()
    
    def calculate_total_trading_hours(self):
        """计算总交易时间点数（从开始日期到结束日期）"""
        if not self.positions_data:
            self.total_trading_hours = 0
            return
        
        try:
            start_date = datetime.strptime(self.positions_data[0]['date'], "%Y-%m-%d %H:%M:%S")
            end_date = datetime.strptime(self.positions_data[-1]['date'], "%Y-%m-%d %H:%M:%S")
            
            # 计算交易天数
            days = (end_date - start_date).days
            if days < 1:
                days = 1
            
            # 每天交易时间：10:00, 11:00, 12:00, 13:00, 14:00, 15:00（共6小时）
            # 总时间点数 = 天数 * 6 + 1（包含最后一个时间点）
            self.total_trading_hours = days * 6 + 1
        except:
            # 如果日期解析失败，使用position数据数量
            self.total_trading_hours = len(self.positions_data)
    
    def get_trade_count_from_log(self) -> int:
        """从log目录获取实际交易次数"""
        # 尝试找到对应的log目录
        # position文件路径通常是: .../agent_data/xxx/position/position.jsonl
        # log目录通常是: .../agent_data/xxx/log/
        pos_file_path = Path(self.position_file)
        
        # 查找log目录
        possible_log_paths = [
            pos_file_path.parent.parent / "log",  # position/../log
            pos_file_path.parent.parent.parent / "log",  # position/../../log
        ]
        
        for log_dir in possible_log_paths:
            if log_dir.exists() and log_dir.is_dir():
                # 统计所有json文件数量
                json_files = list(log_dir.rglob('*.json'))
                if json_files:
                    return len(json_files)
        
        # 如果没有找到log目录，返回None，使用position数据计算
        return None
    
    def calculate_total_asset(self, position: Dict) -> float:
        """计算总资产"""
        if not position or 'positions' not in position:
            return self.initial_cash
        
        cash = position['positions'].get('CASH', 0)
        total_stock_value = 0.0
        
        for symbol, quantity in position['positions'].items():
            if symbol != 'CASH' and quantity != 0:
                price = self.price_cache.get_price(symbol, position['date'])
                total_stock_value += price * quantity
        
        return cash + total_stock_value
    
    def calculate_all_metrics(self) -> Dict:
        """计算所有指标"""
        if not self.positions_data:
            return {}
        
        print(f"  加载了 {len(self.positions_data)} 条position记录")
        
        # 计算净值曲线
        equity_curve = []
        dates = []
        position_values = []  # 持仓市值列表
        total_assets = []  # 总资产列表
        
        for i, pos in enumerate(self.positions_data):
            date = pos['date']
            dates.append(date)
            total_asset = self.calculate_total_asset(pos)
            total_assets.append(total_asset)
            equity_curve.append(total_asset / self.initial_cash)
            
            # 计算持仓市值
            stock_value = 0.0
            for symbol, quantity in pos.get('positions', {}).items():
                if symbol != 'CASH' and quantity != 0:
                    price = self.price_cache.get_price(symbol, date)
                    stock_value += price * quantity
            position_values.append(stock_value)
        
        equity_array = np.array(equity_curve)
        returns = np.diff(equity_array) / equity_array[:-1]  # 收益率序列
        
        # 计算指标
        metrics = {}
        
        # ========== 第一优先级指标 ==========
        
        # 1. 总收益率和年化收益率
        total_return = equity_array[-1] - 1.0
        metrics['总收益率'] = total_return
        
        # 计算实际交易天数
        try:
            start_date = datetime.strptime(dates[0], "%Y-%m-%d %H:%M:%S")
            end_date = datetime.strptime(dates[-1], "%Y-%m-%d %H:%M:%S")
            days_diff = (end_date - start_date).days
            if days_diff < 1:
                days_diff = 1
        except:
            # 如果日期解析失败，使用数据点估算
            days_diff = len(self.positions_data) / 6.5  # 假设每天6.5小时
        
        if days_diff > 0:
            final_equity = equity_array[-1]
            if final_equity <= 0:
                # 如果最终净值小于等于0，年化收益率设为-100%
                annualized_return = -1.0
            else:
                # 标准年化收益率公式: (最终净值)^(365/天数) - 1
                annualized_return = (final_equity ** (365.0 / days_diff)) - 1
                # 检查是否产生了异常值（数值精度问题）
                if np.isnan(annualized_return) or np.isinf(annualized_return):
                    annualized_return = -1.0
                # 如果年化收益率小于-100%，限制在-100%
                elif annualized_return < -1.0:
                    annualized_return = -1.0
        else:
            annualized_return = 0.0
        metrics['年化收益率'] = annualized_return
        
        # 2. 最大回撤
        peak = np.maximum.accumulate(equity_array)
        drawdown = (peak - equity_array) / peak
        max_drawdown = np.max(drawdown)
        metrics['最大回撤(MDD)'] = max_drawdown
        
        # 3. 卡尔玛比率
        if max_drawdown > 0:
            calmar_ratio = annualized_return / max_drawdown
        else:
            calmar_ratio = float('inf') if annualized_return > 0 else 0.0
        metrics['卡尔玛比率'] = calmar_ratio
        
        # 4. 仓位利用率（PU）
        # 对于支持做空的系统，需要重新定义PU
        # 方法：分别计算做多和做空的市值，PU = (做多市值 + 做空市值绝对值) / 总资产
        # 或者更简单：PU = 平均持仓市值绝对值 / 平均总资产（但不能是负数）
        abs_position_values = []  # 使用持仓市值的绝对值
        
        for pos in self.positions_data:
            positions = pos.get('positions', {})
            stock_value_abs = 0.0
            for symbol, quantity in positions.items():
                if symbol != 'CASH' and quantity != 0:
                    price = self.price_cache.get_price(symbol, pos['date'])
                    stock_value_abs += abs(price * quantity)  # 使用绝对值
            abs_position_values.append(stock_value_abs)
        
        avg_abs_position_value = np.mean(abs_position_values)
        avg_total_asset = np.mean(total_assets)
        
        # 使用平均总资产，如果总资产很小或为负，使用初始资金
        if avg_total_asset > self.initial_cash * 0.1:  # 总资产大于初始资金的10%
            position_utilization = avg_abs_position_value / avg_total_asset
        else:
            # 如果总资产太小或为负，使用初始资金作为分母
            position_utilization = avg_abs_position_value / self.initial_cash if self.initial_cash > 0 else 0.0
        
        # 仓位利用率不能是负数
        position_utilization = max(0.0, position_utilization)
        metrics['仓位利用率(PU)'] = position_utilization
        
        # 5-6. Entry/Exit Quality
        entry_qualities = self.calculate_entry_exit_quality()
        for n in ENQ_WINDOWS:
            entry_val = entry_qualities.get(f'entry_{n}', None)
            exit_val = entry_qualities.get(f'exit_{n}', None)
            metrics[f'Entry Quality (N={n})'] = entry_val
            metrics[f'Exit Quality (N={n})'] = exit_val
        
        # 7. 交易频率
        # 优先从log目录获取交易次数（因为valuecell等文件可能不包含no_trade记录）
        trade_count_from_log = self.get_trade_count_from_log()
        
        if trade_count_from_log is not None:
            # 使用log目录的json文件数量作为交易次数
            trade_count = trade_count_from_log
            # 使用总交易时间点数计算频率
            total_hours = self.total_trading_hours if self.total_trading_hours else len(self.positions_data)
            trading_frequency = trade_count / total_hours if total_hours > 0 else 0
        else:
            # 如果没有log目录，使用position数据中的交易动作数
            trade_count = sum(1 for pos in self.positions_data 
                             if pos.get('this_action', {}).get('action') in ['buy', 'sell'])
            trading_frequency = trade_count / len(self.positions_data) if self.positions_data else 0
        
        metrics['交易频率'] = trading_frequency
        metrics['交易次数'] = trade_count
        
        # 8-9. 胜率和盈亏比
        win_rate, profit_loss_ratio = self.calculate_win_rate()
        metrics['胜率'] = win_rate
        metrics['盈亏比'] = profit_loss_ratio
        
        # ========== 第二优先级指标 ==========
        
        # 10. 夏普比率
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252 * 6.5)  # 年化
        else:
            sharpe_ratio = 0.0
        metrics['夏普比率'] = sharpe_ratio
        
        # 11. 波动率
        if len(returns) > 0:
            volatility = np.std(returns) * np.sqrt(252 * 6.5)  # 年化波动率
        else:
            volatility = 0.0
        metrics['波动率'] = volatility
        
        # 12. 持仓集中度
        concentration = self.calculate_concentration()
        metrics['平均持仓集中度'] = concentration.get('avg', 0.0)
        metrics['最大持仓集中度'] = concentration.get('max', 0.0)
        
        # 13. 平均持仓时间
        avg_holding_period = self.calculate_holding_period()
        metrics['平均持仓时间(小时)'] = avg_holding_period
        
        # 14. 连续盈亏次数
        consecutive_stats = self.calculate_consecutive_wins_losses()
        metrics['最大连续盈利次数'] = consecutive_stats.get('max_wins', 0)
        metrics['最大连续亏损次数'] = consecutive_stats.get('max_losses', 0)
        
        return metrics
    
    def calculate_entry_exit_quality(self) -> Dict:
        """计算Entry和Exit Quality"""
        entry_qualities = {f'entry_{n}': [] for n in ENQ_WINDOWS}
        exit_qualities = {f'exit_{n}': [] for n in ENQ_WINDOWS}
        
        for pos in self.positions_data:
            action = pos.get('this_action', {})
            action_type = action.get('action', '')
            symbol = action.get('symbol', '')
            date = pos.get('date', '')
            
            # 获取价格：优先使用this_action中的price，如果没有则从价格数据获取
            price = action.get('price', 0)
            if price <= 0:
                # 如果没有price字段，从价格数据中获取当时的市场价格
                price = self.price_cache.get_price(symbol, date)
            
            if action_type == 'buy' and price > 0:
                # 计算Entry Quality
                for n in ENQ_WINDOWS:
                    future_low = self.price_cache.get_future_low(symbol, date, n)
                    if future_low and future_low > 0:
                        enq = price / future_low
                        entry_qualities[f'entry_{n}'].append(enq)
            
            elif action_type == 'sell' and price > 0:
                # 计算Exit Quality
                for n in ENQ_WINDOWS:
                    future_high = self.price_cache.get_future_high(symbol, date, n)
                    if future_high and future_high > 0:
                        exq = price / future_high
                        exit_qualities[f'exit_{n}'].append(exq)
        
        result = {}
        for n in ENQ_WINDOWS:
            entry_list = entry_qualities[f'entry_{n}']
            exit_list = exit_qualities[f'exit_{n}']
            # 只计算有数据的平均值
            if entry_list:
                result[f'entry_{n}'] = float(np.mean(entry_list))
            else:
                result[f'entry_{n}'] = None
            if exit_list:
                result[f'exit_{n}'] = float(np.mean(exit_list))
            else:
                result[f'exit_{n}'] = None
        
        return result
    
    def calculate_win_rate(self) -> Tuple[float, float]:
        """计算胜率和盈亏比"""
        trades = []  # 存储每笔交易的收益
        
        # 配对买卖交易
        open_positions = {}  # {symbol: [(buy_price, buy_date, quantity), ...]}
        
        for pos in self.positions_data:
            action = pos.get('this_action', {})
            action_type = action.get('action', '')
            symbol = action.get('symbol', '')
            amount = action.get('amount', 0)
            date = pos.get('date', '')
            
            # 获取价格：优先使用this_action中的price，如果没有则从价格数据获取
            price = action.get('price', 0)
            if price <= 0:
                price = self.price_cache.get_price(symbol, date)
            
            if action_type == 'buy' and amount > 0 and price > 0:
                if symbol not in open_positions:
                    open_positions[symbol] = []
                open_positions[symbol].append((price, date, amount))
            
            elif action_type == 'sell' and amount > 0 and price > 0:
                if symbol in open_positions and open_positions[symbol]:
                    # FIFO原则匹配
                    remaining = amount
                    while remaining > 0 and open_positions[symbol]:
                        buy_price, buy_date, buy_amount = open_positions[symbol][0]
                        sell_amount = min(remaining, buy_amount)
                        profit = (price - buy_price) * sell_amount
                        trades.append(profit)
                        
                        if sell_amount >= buy_amount:
                            open_positions[symbol].pop(0)
                        else:
                            open_positions[symbol][0] = (buy_price, buy_date, buy_amount - sell_amount)
                        remaining -= sell_amount
        
        if not trades:
            return 0.0, 0.0
        
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t < 0]
        
        win_rate = len(wins) / len(trades) if trades else 0.0
        
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = abs(np.mean(losses)) if losses else 0.0
        
        if avg_loss > 0:
            profit_loss_ratio = avg_win / avg_loss
        else:
            profit_loss_ratio = float('inf') if avg_win > 0 else 0.0
        
        return win_rate, profit_loss_ratio
    
    def calculate_concentration(self) -> Dict[str, float]:
        """计算持仓集中度"""
        concentrations = []
        
        for pos in self.positions_data:
            positions = pos.get('positions', {})
            total_asset = self.calculate_total_asset(pos)
            
            if total_asset > 0:
                max_position_value = 0.0
                for symbol, quantity in positions.items():
                    if symbol != 'CASH' and quantity != 0:
                        price = self.price_cache.get_price(symbol, pos['date'])
                        position_value = abs(price * quantity)  # 使用绝对值，因为做空时是负数
                        if position_value > max_position_value:
                            max_position_value = position_value
                
                # 使用总资产的绝对值，避免负数
                abs_total_asset = abs(total_asset)
                concentration = max_position_value / abs_total_asset if abs_total_asset > 0 else 0.0
                # 确保集中度在0-1之间
                concentration = min(1.0, max(0.0, concentration))
                concentrations.append(concentration)
            elif total_asset <= 0:
                # 如果总资产为负或零，使用初始资金作为分母
                max_position_value = 0.0
                for symbol, quantity in positions.items():
                    if symbol != 'CASH' and quantity != 0:
                        price = self.price_cache.get_price(symbol, pos['date'])
                        position_value = abs(price * quantity)
                        if position_value > max_position_value:
                            max_position_value = position_value
                
                if self.initial_cash > 0:
                    concentration = max_position_value / self.initial_cash
                    concentration = min(1.0, max(0.0, concentration))
                    concentrations.append(concentration)
        
        return {
            'avg': np.mean(concentrations) if concentrations else 0.0,
            'max': np.max(concentrations) if concentrations else 0.0
        }
    
    def calculate_holding_period(self) -> float:
        """计算平均持仓时间"""
        holding_periods = []
        open_positions = {}  # {symbol: {open_date: quantity}}
        
        for i, pos in enumerate(self.positions_data):
            action = pos.get('this_action', {})
            action_type = action.get('action', '')
            symbol = action.get('symbol', '')
            amount = action.get('amount', 0)
            date = pos.get('date', '')
            
            if action_type == 'buy' and amount > 0:
                if symbol not in open_positions:
                    open_positions[symbol] = {}
                # 简化：使用当前索引作为时间戳
                open_positions[symbol][i] = amount
            
            elif action_type == 'sell' and amount > 0:
                if symbol in open_positions:
                    remaining = amount
                    closed_dates = []
                    for open_date_idx in sorted(open_positions[symbol].keys()):
                        if remaining <= 0:
                            break
                        open_qty = open_positions[symbol][open_date_idx]
                        sell_qty = min(remaining, open_qty)
                        holding_periods.append(i - open_date_idx)
                        remaining -= sell_qty
                        if sell_qty >= open_qty:
                            closed_dates.append(open_date_idx)
                    
                    for closed_date in closed_dates:
                        del open_positions[symbol][closed_date]
        
        return np.mean(holding_periods) if holding_periods else 0.0
    
    def calculate_consecutive_wins_losses(self) -> Dict[str, int]:
        """计算连续盈亏次数"""
        trades = []
        
        # 获取所有交易的收益
        open_positions = {}
        for pos in self.positions_data:
            action = pos.get('this_action', {})
            action_type = action.get('action', '')
            symbol = action.get('symbol', '')
            amount = action.get('amount', 0)
            date = pos.get('date', '')
            
            # 获取价格：优先使用this_action中的price，如果没有则从价格数据获取
            price = action.get('price', 0)
            if price <= 0:
                price = self.price_cache.get_price(symbol, date)
            
            if action_type == 'buy' and amount > 0 and price > 0:
                if symbol not in open_positions:
                    open_positions[symbol] = []
                open_positions[symbol].append((price, amount))
            
            elif action_type == 'sell' and amount > 0 and price > 0:
                if symbol in open_positions and open_positions[symbol]:
                    remaining = amount
                    while remaining > 0 and open_positions[symbol]:
                        buy_price, buy_amount = open_positions[symbol][0]
                        sell_amount = min(remaining, buy_amount)
                        profit = (price - buy_price) * sell_amount
                        trades.append(1 if profit > 0 else -1)
                        
                        if sell_amount >= buy_amount:
                            open_positions[symbol].pop(0)
                        else:
                            open_positions[symbol][0] = (buy_price, buy_amount - sell_amount)
                        remaining -= sell_amount
        
        if not trades:
            return {'max_wins': 0, 'max_losses': 0}
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in trades:
            if trade > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return {'max_wins': max_wins, 'max_losses': max_losses}


def format_value(value, is_percentage=False) -> str:
    """格式化指标值"""
    if value is None:
        return "N/A"
    elif isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return "N/A"
        elif abs(value) < 0.0001:
            return "0.0000"
        elif is_percentage:
            # 百分比格式（乘以100）
            return f"{value * 100:.2f}%"
        elif abs(value) < 0.01:
            return f"{value:.4f}"
        elif abs(value) < 1:
            return f"{value:.4f}"
        elif abs(value) < 100:
            return f"{value:.2f}"
        else:
            return f"{value:.2f}"
    else:
        return str(value)


def print_metrics_table(results: List[Tuple[str, Dict]]):
    """打印指标表格"""
    if not results:
        print("没有可显示的结果")
        return
    
    # 获取所有指标的键
    all_keys = set()
    for _, metrics in results:
        all_keys.update(metrics.keys())
    
    # 按优先级排序指标
    priority_keys = [
        '总收益率', '年化收益率', '最大回撤(MDD)', '卡尔玛比率', '仓位利用率(PU)',
        'Entry Quality (N=1)', 'Entry Quality (N=3)', 'Entry Quality (N=5)', 'Entry Quality (N=10)',
        'Exit Quality (N=1)', 'Exit Quality (N=3)', 'Exit Quality (N=5)', 'Exit Quality (N=10)',
        '交易频率', '交易次数', '胜率', '盈亏比',
        '夏普比率', '波动率', '平均持仓集中度', '最大持仓集中度',
        '平均持仓时间(小时)', '最大连续盈利次数', '最大连续亏损次数'
    ]
    
    # 添加其他未列出的指标
    other_keys = sorted(all_keys - set(priority_keys))
    ordered_keys = [k for k in priority_keys if k in all_keys] + other_keys
    
    # 计算列宽
    max_name_len = max(len(name) for name, _ in results)
    max_key_len = max(len(k) for k in ordered_keys)
    col_width = max(15, max_name_len)
    
    # 打印表头
    header = f"{'指标':<{max_key_len}}"
    separator = "-" * max_key_len
    for name, _ in results:
        header += f" | {name:<{col_width}}"
        separator += "-+-" + "-" * col_width
    print(header)
    print(separator)
    
    # 需要显示为百分比的指标
    percentage_keys = {'总收益率', '年化收益率', '最大回撤(MDD)', '仓位利用率(PU)', '胜率', '波动率', 
                      '平均持仓集中度', '最大持仓集中度'}
    
    # 打印每一行指标
    for key in ordered_keys:
        row = f"{key:<{max_key_len}}"
        is_pct = key in percentage_keys
        for _, metrics in results:
            value = metrics.get(key, None)
            formatted = format_value(value, is_percentage=is_pct)
            row += f" | {formatted:>{col_width}}"
        print(row)


def extract_display_name(path: str, custom_name: str = None) -> str:
    """从路径提取或生成显示名称"""
    if custom_name:
        return custom_name
    
    path_obj = Path(path)
    path_parts = path_obj.parts
    
    # 尝试从路径中提取有意义的名称
    # 例如：data/agent_data/deepseek/deepseek-v3-whole-month/position/position.jsonl
    # 提取：deepseek-v3-whole-month
    if len(path_parts) >= 3:
        # 通常agent_data下的目录结构是: agent_data/模型名/实验名/position/position.jsonl
        if "agent_data" in path_parts:
            idx = list(path_parts).index("agent_data")
            if idx + 2 < len(path_parts):
                # 取实验名作为显示名称
                return path_parts[idx + 2]
    
    # 如果提取失败，使用父目录名
    if len(path_parts) >= 2:
        return f"{path_parts[-2]}/{path_parts[-1]}"
    else:
        return path_obj.name


def parse_position_files_config(config):
    """解析position文件配置，支持字典列表或字符串列表"""
    file_list = []
    
    if not config:
        return file_list
    
    for item in config:
        if isinstance(item, dict):
            # 字典格式：{"name": "显示名称", "path": "文件路径"}
            if "path" in item:
                custom_name = item.get("name", None)
                display_name = extract_display_name(item["path"], custom_name)
                file_list.append({
                    "name": display_name,
                    "path": item["path"]
                })
        elif isinstance(item, str):
            # 字符串格式：直接是文件路径
            display_name = extract_display_name(item)
            file_list.append({
                "name": display_name,
                "path": item
            })
    
    return file_list


def main():
    """主函数"""
    # 解析配置的路径，如果没有配置则使用命令行参数
    if POSITION_FILES:
        file_configs = parse_position_files_config(POSITION_FILES)
        print("=" * 80)
        print(f"使用代码中配置的文件路径（共 {len(file_configs)} 个文件）")
        print("=" * 80)
    elif len(sys.argv) >= 2:
        # 命令行参数格式
        file_configs = []
        for path in sys.argv[1:]:
            display_name = extract_display_name(path)
            file_configs.append({
                "name": display_name,
                "path": path
            })
        print("使用命令行参数中的文件路径")
    else:
        print("=" * 80)
        print("交易Agent量化指标计算工具")
        print("=" * 80)
        print("\n使用方法:")
        print("  方法1: 在代码中的 POSITION_FILES 列表里直接配置路径和名称（推荐）")
        print("  方法2: python calculate_metrics.py <position_file1> [position_file2] ...")
        print("\n示例（方式1 - 推荐）:")
        print("    POSITION_FILES = [")
        print("        {'name': '显示名称1', 'path': 'data/agent_data/.../position.jsonl'},")
        print("        {'name': '显示名称2', 'path': 'data/agent_data/.../position.jsonl'},")
        print("    ]")
        print("\n示例（方式2 - 简单路径）:")
        print("    POSITION_FILES = [")
        print("        'data/agent_data/.../position.jsonl',")
        print("        'data/agent_data/.../position.jsonl',")
        print("    ]")
        print("\n  或使用命令行:")
        print("    python calculate_metrics.py file1.jsonl file2.jsonl file3.jsonl")
        print("\n注意:")
        print("  - 价格数据文件应位于 data/ 目录下")
        print("  - 支持同时处理多个position文件，结果将以表格形式对比显示")
        print("=" * 80)
        sys.exit(1)
    
    price_dir = PRICE_DIR
    
    # 检查价格数据目录
    if not price_dir.exists():
        print(f"警告: 价格数据目录不存在: {price_dir}")
        print("请确保价格数据文件在 data/ 目录下")
        sys.exit(1)
    
    results = []
    
    print(f"\n处理 {len(file_configs)} 个position文件...")
    print("=" * 80)
    
    for idx, file_config in enumerate(file_configs, 1):
        pos_file = file_config["path"]
        display_name = file_config["name"] if file_config["name"] else pos_file
        
        print(f"\n[{idx}/{len(file_configs)}] 正在处理: {display_name}")
        print(f"    路径: {pos_file}")
        try:
            calculator = MetricsCalculator(pos_file, price_dir)
            metrics = calculator.calculate_all_metrics()
            
            results.append((display_name, metrics))
            print(f"  ✓ 完成，计算了 {len(metrics)} 个指标")
        except Exception as e:
            print(f"  ✗ 错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("\n指标计算结果:\n")
    print_metrics_table(results)


if __name__ == "__main__":
    main()

