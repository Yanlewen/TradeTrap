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

## 3. Optional: baseline reference line

The chart automatically draws a grey reference line representing the initial capital ($5,000). QQQ benchmarking can be re-enabled by providing a `data/Adaily_prices_QQQ.json` file and restoring the related logic in `data-loader.js` if needed.

---

With this setup, switching between DeepSeek, Claude, GPT or any other agent family is now a configuration-only change: run the preprocessor to produce a JSON, point `dataset_config.json` to it, and set the desired labels/colours.
