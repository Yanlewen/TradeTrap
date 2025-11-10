# Prompt Injection 插件

位置：`agent/plugins/`，规则文件：`prompts/prompt_injections.json`。

## 文件简介
- `prompt_injection_manager.py`：加载规则，按阶段/日期/时间/签名决定是否注入。
- `prompt_injection_agent.py`：日频包装器（继承 `BaseAgent`）。
- `prompt_injection_agent_hour.py`：小时包装器（继承 `BaseAgent_Hour`）。

## 规则要点
- 规则写在 `prompts/prompt_injections.json` 的 `injections` 数组中。
- 支持字段：
  - `id`：唯一标识，便于日志识别。
  - `enabled`：布尔值，默认 `true`。
  - `stage`：当前仅支持 `pre_decision`。
  - `match`（可选）：
    - `signature`：字符串或列表，仅匹配指定代理签名。
    - `dates`：字符串或列表（`YYYY-MM-DD`）；也可使用 `start_date`、`end_date`。
    - `datetime_range`：`{ "start": ISO8601, "end": ISO8601 }`。
    - `time_range`：`{ "start": "HH:MM", "end": "HH:MM" }`。
    - `times`：字符串或列表，指定准确的 `HH:MM`。
    - `weekdays`：数字（`0`=周一）或名称（`"mon"`、`"monday"`...）。
    - `timezone`：IANA 时区名（如 `"UTC"`、`"Asia/Shanghai"`）。
  - `messages`：消息列表，格式为 `{ "role": "...", "content": "..." }`。
- `match` 中未填写的条件视为无限制；同一时间可命中多条规则。

## 启用方法
- 在代码中直接使用 `PromptInjectionAgent` / `PromptInjectionAgentHour`，
  或在 JSON 配置（如 `configs/my_config.json`）中设置：

```json
{
  "agent_type": "PromptInjectionAgent",
  ...
}
```

小时级：

```json
{
  "agent_type": "PromptInjectionAgent_Hour",
  ...
}
```

- 请确保 `main.py` 的 `AGENT_REGISTRY` 含有：

```python
"PromptInjectionAgent": {
    "module": "agent.plugins.prompt_injection_agent",
    "class": "PromptInjectionAgent"
},
"PromptInjectionAgent_Hour": {
    "module": "agent.plugins.prompt_injection_agent_hour",
    "class": "PromptInjectionAgentHour"
},
```

## 提示
- 为每条注入设置唯一 `id`，便于排查。
- 日志位于 `data/agent_data/<signature>/log/.../log.jsonl`。
