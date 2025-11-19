#!/bin/bash

# Get the TradeTrap root directory (parent of AI-Trader/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AI_TRADER_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PROJECT_ROOT="$( cd "$AI_TRADER_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo "🔧 Now starting MCP services..."
cd "$AI_TRADER_DIR/agent_tools"
python start_mcp_services.py
cd "$PROJECT_ROOT"
