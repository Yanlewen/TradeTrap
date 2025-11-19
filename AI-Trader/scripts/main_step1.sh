#!/bin/bash

# prepare data

# Get the TradeTrap root directory (parent of AI-Trader/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AI_TRADER_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PROJECT_ROOT="$( cd "$AI_TRADER_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

cd data
# python get_daily_price.py #run daily price data
python get_interdaily_price.py #run interdaily price data
python merge_jsonl.py
cd ..
