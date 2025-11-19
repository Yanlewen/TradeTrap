#!/bin/bash

# Get the TradeTrap root directory (parent of AI-Trader/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AI_TRADER_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PROJECT_ROOT="$( cd "$AI_TRADER_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "🤖 正在启动主交易智能体（A股模式）..."

python main.py configs/astock_config.json  # 运行A股配置

echo "✅ AI-Trader 已停止"
