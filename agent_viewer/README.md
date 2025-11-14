# Agent Dashboard Usage Guide

This dashboard is now fully driven by JSON files located under `agent_viewer/data`. Follow the steps below whenever you want to visualise a different set of agent runs.

## 1. Generate the dataset JSON

1. Place your agent run folders under `AI-Trader/data/agent_data/` (or provide another absolute/relative path).
2. Edit `preprocess_data.py` and adjust the `AGENTS` list—each entry can specify a custom name and path:
   ```python
   AGENTS = [
       {"name": "claude-3.7-sonnet", "path": "claude/claude-3.7-sonnet"},
       {"name": "claude-3.7-sonnet-with-news", "path": "claude/claude-3.7-sonnet-with-news"},
       {"name": "claude-3.7-sonnet-ReverseExpectations", "path": "claude/claude-3.7-sonnet-ReverseExpectations"}
   ]
   ```
3. Run the script from the `agent_viewer` directory:
   ```bash
   python3 preprocess_data.py
   ```
   The script produces a JSON file (for example `data/agents_data_claude.json`) containing positions, logs, and summary stats for the selected signatures.

## 2. Configure what the front-end displays

The dashboard reads `data/dataset_config.json` to decide which signatures to plot, how to label them, and what colours to use. Structure:
```json
{
  "source": "agents_data_claude.json",
  "datasets": [
    {
      "id": "claude-3.7-sonnet",
      "label": "Claude Sonnet",
      "color": "#f5cb5c",
      "description": "Baseline claude configuration"
    }
  ]
}
```
- `source`: file inside `agent_viewer/data/` (or a full URL) that contains the dataset produced by `preprocess_data.py`.
- `datasets`: list of signatures to show. Each entry supports:
  - `id`: signature name (must match the key inside the dataset JSON).
  - `label`: human-readable legend/checkbox text.
  - `color`: hex colour used for the chart line.
  - `description` (optional): appears under the checkbox label.

After editing `dataset_config.json`, simply refresh the dashboard in the browser (hard refresh `Ctrl/Cmd + Shift + R` recommended) and the new selection will render automatically—no additional code changes required.

## 3. Optional: baseline / benchmark line

`dataset_config.json` 支持一个 `baseline` 段，允许自定义基准线：
```json
{
  "baseline": {
    "type": "price_series",
    "label": "QQQ Benchmark",
    "source": "Adaily_prices_QQQ.json",
    "initial_capital": 5000,
    "color": "#94a3b8"
  }
}
```
- `type`: 支持 `price_series`（将价格转成资产价值）或 `constant`（固定数值）。如果设置为 `none` 或删除该段，则不渲染基准线，前端会默认显示常量 `$5,000`。
- `source`: 指向 `agent_viewer/data/` 下的价格 JSON（或 URL），格式可为 AlphaVantage Time Series、自定义 `{ dates, values }`、或 `{ timestamp: close }`。
- `initial_capital`: 用于将价格系列转换成“如果以该资金买入”的资产曲线（仅 `price_series` 生效）。
- `label` / `color`: 控制图例名称与曲线颜色。

若省略 `baseline` 字段，系统会绘制默认的 "Initial Balance ($5,000)" 虚线基准。需要换成其他标的（例如 `daily_prices_NVDA.json`）时，只需调整 `baseline` 中的配置并刷新页面。

---

With this setup, switching between DeepSeek, Claude, GPT or any other agent family is now a configuration-only change: run the preprocessor to produce a JSON, point `dataset_config.json` to it, and set the desired labels/colours.
