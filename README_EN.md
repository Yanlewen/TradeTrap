# Prompt Injection Plugins

Location: `agent/plugins/` (rules in `prompts/prompt_injections.json`).

## Files
- `prompt_injection_manager.py`: loads rules, matches by stage/date/time/signature.
- `prompt_injection_agent.py`: daily wrapper around `BaseAgent`.
- `prompt_injection_agent_hour.py`: hourly wrapper around `BaseAgent_Hour`.

## Config rules
- Rules live under the `injections` array in `prompts/prompt_injections.json`.
- Supported keys inside each rule:
  - `id` (string): identifier for logging/debug.
  - `enabled` (bool, default `true`).
  - `stage` (string): currently `pre_decision`.
  - `match` (object, optional):
    - `signature`: string or list; inject only for matching agent signatures.
    - `dates`: string or list of `YYYY-MM-DD`; `start_date` / `end_date` also supported.
    - `datetime_range`: `{ "start": ISO8601, "end": ISO8601 }`.
    - `time_range`: `{ "start": "HH:MM", "end": "HH:MM" }`.
    - `times`: string or list of `HH:MM`.
    - `weekdays`: integers (`0`=Mon) or names (`"mon"`, `"monday"`, …).
    - `timezone`: IANA name (e.g. `"UTC"`, `"America/New_York"`).
  - `messages` (array): ordered list of `{ "role": "...", "content": "..." }`.
- Anything omitted in `match` is treated as no restriction; multiple rules can fire in the same run.

## Enable wrappers
- Instantiate `PromptInjectionAgent` / `PromptInjectionAgentHour`, or
  set in JSON config (e.g. `configs/my_config.json`):

```json
{
  "agent_type": "PromptInjectionAgent/PromptInjectionAgent_Hour",
  ...
}
```

- Ensure `main.py` registers both entries:

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

## Tips
- Give each injection a unique `id`.
- Check `data/agent_data/<signature>/log/.../log.jsonl` to confirm injections.
