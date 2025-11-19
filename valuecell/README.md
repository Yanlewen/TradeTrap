# Auto Trading Standalone Module

一个独立的自动交易模块，集成到 TradeTrap 项目中。该模块提供完全自动化的交易策略执行，结合技术分析和 AI 信号生成。

## 特性

- ✅ 完全自动化交易执行
- ✅ 技术分析 + AI 驱动的交易信号
- ✅ 支持股票和加密货币市场
- ✅ 投资组合决策管理
- ✅ Paper Trading（回测模式）
- ✅ 基于 Pydantic 的配置管理

## 架构设计

```
valuecell/
├── auto_trading_agent/
│   ├── agent.py                    # 统一入口（Factory Pattern）
│   ├── base/                       # 基类
│   │   ├── base_agent.py          # 核心交易逻辑
│   │   └── base_config.py         # 配置基类
│   ├── stock/                      # 股票交易
│   │   ├── stock_agent.py
│   │   └── stock_config.py
│   ├── crypto/                     # 加密货币交易
│   │   ├── crypto_agent.py
│   │   └── crypto_config.py
│   ├── exchanges/                  # 交易所适配器
│   │   ├── paper_trading.py       # Paper Trading
│   │   ├── okx_exchange.py        # OKX
│   │   └── binance_exchange.py    # Binance
│   ├── market_data.py             # 行情数据获取
│   ├── technical_analysis.py      # 技术分析
│   ├── portfolio_decision_manager.py  # 投资组合决策
│   ├── position_manager.py        # 仓位管理
│   ├── trading_executor.py        # 交易执行
│   └── trade_recorder.py          # 交易记录
└── README.md
```

## 在 TradeTrap 中使用

### 1. 配置文件

使用以下配置文件之一：

- `configs/default_auto_trading_standalone_config.json` - 加密货币配置
- `configs/default_auto_trading_stock_config.json` - 股票配置
- `configs/valuecell_config.json` - 完整示例配置

### 2. 运行

```bash
cd /Users/meijilin/Documents/项目/TradeTrap/AI-Trader

# 使用加密货币配置
python main.py configs/default_auto_trading_standalone_config.json

# 使用股票配置
python main.py configs/default_auto_trading_stock_config.json

# 使用自定义配置
python main.py configs/valuecell_config.json
```

### 3. 配置说明

配置文件示例：

```json
{
  "agent_type": "Valuecell",
  "market": "us",
  "date_range": {
    "init_date": "2025-10-02 10:00:00",
    "end_date": "2025-10-31 15:00:00"
  },
  "models": [
    {
      "name": "gpt-4o-mini",
      "basemodel": "openai/gpt-4o-mini",
      "signature": "auto-trading-stock-gpt-4o-mini",
      "enabled": true
    }
  ],
  "agent_config": {
    "initial_capital": 100000.0,
    "market_type": "stock",           // 或 "crypto"
    "stock_symbols": null,             // null 使用默认 NASDAQ 100
    "market": "us",                    // 或 "cn"
    "check_interval": 60,
    "risk_per_trade": 0.05,
    "max_positions": 5,
    "use_ai_signals": true,
    "exchange": "paper",
    "min_bars_daily": 10,
    "min_bars_hourly": 6,
    "data_period_daily": "10d",
    "data_period_hourly": "1d"
  },
  "log_config": {
    "log_path": "./data/agent_data"
  }
}
```

#### 关键配置项

**agent_config 参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `market_type` | 市场类型：`stock` 或 `crypto` | `crypto` |
| `initial_capital` | 初始资金 | 100000.0 |
| `stock_symbols` | 股票列表，null 使用默认 | null |
| `crypto_symbols` | 加密货币列表（仅 crypto 模式） | `["BTC-USD", "ETH-USD"]` |
| `market` | 股票市场：`us` 或 `cn`（仅 stock 模式） | `us` |
| `check_interval` | 检查间隔（秒） | 60 |
| `risk_per_trade` | 每笔交易风险比例 | 0.05 |
| `max_positions` | 最大持仓数 | 5 |
| `use_ai_signals` | 是否使用 AI 信号 | true |
| `exchange` | 交易所（目前仅支持 `paper`） | `paper` |
| `min_bars_daily` | 最少日线数据条数 | 15 |
| `min_bars_hourly` | 最少小时线数据条数 | 50 |
| `data_period_daily` | 日线数据周期 | `30d` |
| `data_period_hourly` | 小时线数据周期 | `5d` |

## 与其他 Agent 的区别

### Valuecell vs BaseAgent

| 特性 | Valuecell | BaseAgent/PositionAttackAgent |
|------|----------------------|------------------------------|
| **架构** | Pydantic 配置 + Factory Pattern | 直接实例化 |
| **初始化** | 不需要 `initialize()` | 需要 `initialize()` 连接 MCP |
| **配置方式** | config_dict + 多个专用配置类 | 构造函数参数 |
| **市场支持** | Stock + Crypto（统一接口） | 分离的 BaseAgent/BaseAgentCrypto |
| **交易所** | 模块化适配器（支持扩展） | 内置逻辑 |
| **代码风格** | 现代化、类型安全 | 传统风格 |

### 为什么选择 Valuecell？

1. **更清晰的架构**：基于 Pydantic 的配置管理，类型安全
2. **易于扩展**：模块化设计，易于添加新的交易所或市场
3. **统一接口**：Stock 和 Crypto 使用相同的 API
4. **独立运行**：可以独立于 TradeTrap 运行（通过 `run_agent.py`）

## 依赖项

已自动添加到 `requirements.txt`：

```
pydantic>=2.0.0
pandas>=2.0.0
pytz>=2023.3
```

## 注意事项

1. **行情数据**：使用 yfinance 自动获取历史数据
2. **Paper Trading**：当前仅支持回测模式，不支持实盘交易
3. **AI 模型**：需要配置 OpenAI API Key（通过环境变量或配置文件）
4. **日期格式**：支持 `YYYY-MM-DD` 和 `YYYY-MM-DD HH:MM:SS` 两种格式

## 输出示例

```
✅ Valuecell instance created successfully
📊 Running trading for date range: 2025-10-02 10:00:00 to 2025-10-31 15:00:00
🔄 [2025-10-02 10:00:00] Check #1
📈 Technical Analysis Results:
   AAPL: BUY LONG (Score: 0.75)
   GOOGL: HOLD (Score: 0.45)
🤖 AI Signal Generation...
💼 Portfolio Decision: BUY AAPL (Quantity: 100)
✅ Trade executed: BUY LONG AAPL @$150.25 x100
💰 Portfolio Value: $101,234.56 (+1.23%)
```

## 技术支持

- 原始模块来自 valuecell 项目
- 集成到 TradeTrap by @meijilin
- 如遇问题，请查看 `main.py` 中的 Valuecell 处理逻辑
