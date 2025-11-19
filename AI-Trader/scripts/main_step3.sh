#!/bin/bash

# Get the TradeTrap root directory (parent of AI-Trader/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AI_TRADER_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PROJECT_ROOT="$( cd "$AI_TRADER_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "🤖 Now starting the main trading agent..."

# Please create the config file first!!

# python main.py configs/default_day_config.json #run daily config
python main.py configs/default_hour_config.json #run hourly config

echo "✅ AI-Trader stopped"
