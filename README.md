<div align="center">
<h1 style="margin: 0; display: inline-flex; align-items: center; gap: 12px;">
  <span> 🧨  TradeTrap: Are LLM-based Trading Agents Truly Reliable and Faithful?</span>
</h1>

<div align="center" style="line-height: 2;">
    <a href="https://www.python.org/downloads" target="_blank">
        <img src="https://img.shields.io/badge/python-3.10+-blue.svg"
            alt="Python version"></a>
    <a href="LICENSE" target="_blank">
        <img src="https://img.shields.io/badge/license-Apache2.0-red.svg"
            alt="License: Apache2.0"></a>  

    
</div>

<div align="center" style="margin-top: 2px; gap: 20px; display: inline-flex;">
  <a href="README.md" style="color: auto; text-decoration: none; padding: 0 12px;">English</a>
  <a href="README_CN.md" style="color: gray; text-decoration: none; padding: 0 12px;">中文</a>
</div>


</div>

---
**TradeTrap** is a community-driven and developer-friendly tool for testing LLM-based trading Agents' reliability. A slight perturbation to the input instructions for LLM-based agents can upend an entire investment scheme！Therefore, our mission is to build the reliable financial agent community. Welcome to share feedback and issues you encounter, and invite more developers to contribute 🚀🚀🚀
<div align="center">
  <strong>Multi-Model Breakdown Under Identical Exploits</strong><br/>
  <img src="assets/final_assets_from_positions.png" alt="All Models Exploit Overview" width="880" />
  </em>
</div>





## Overall Potential Vulnerability in Financial Trading Agents
<div align="center">
  <img src="assets/frame.jpeg" alt="Attack_overall_framework" width="820" />
</div>


  - Market Intelligence
    - Data fabrication (indirect prompt injection) → panic sell-offs and irrational buying cascades.
    - MCP tool hijacking → polluted responses steer the planner straight off a cliff.
  - Strategy Formulation
    - Direct prompt injection → catastrophic pivots like forced liquidation and margin wipeouts.
    - Model backdoor → hidden triggers siphon assets on demand.
    - Malicious collusion → compromised sub-agents twist shared decision loops.
  - Portfolio & Ledger
    - Memory poisoning → strategy drift causes the model to learn incorrect experiences.
    - State tampering → cognitive confusion regarding one's own positions/order status.
  - Trading Execution
    - Latency flooding / DoS → missed exits, frozen hedges, unstoppable drawdowns.
    - Tool misuse → execution of unintended orders, violation of risk/compliance rules.


---
## ⚠️ What can you do with TradeTrap?
Currently, we provides a set of plug-and-play attack modules designed to integrate directly with the AI-Trader platform. Once connected, these plugins can actively interfere with a running LLM trading agent, allowing you to test its resilience in real-time through two primary attack vectors:
- Prompt Injection
  - Reverse Expectation: Invert the agent's interpretation of market signals, causing it to make bullish moves in bearish conditions and vice versa.
  - Reverse Actions: Tamper with the historical or simulated outcome data the agent receives, leading to flawed strategy adjustments based on a fabricated past.
- MCP Tool Hijacking
  - Seize control of the agent's external data sources—such as price feeds, news APIs, or social sentiment tools—and replace real-world data with manipulated streams to steer its decisions off-course.

For example:

<div align="center" style="margin-bottom: 24px;">
  <img src="assets/agent-legend.png" alt="Agent Comparison Legend" width="600" />
</div>

<div align="center" style="margin: 12px 0 6px; font-size: 13px; line-height: 1.7; font-weight: 500;">
  🟨 <strong>yellow</strong>：baseline runs without external signals.<br/>
  🔵 <strong>blue</strong>：news-enhanced runs wire into X/Twitter and Reddit feeds.<br/>
  🔴 <strong>red</strong>：poisoned agents tasked with the same capital.
</div>

<p align="center" style="margin: 0 0 18px; font-style: italic; font-size: 12px;">All start with USD 5,000 - watch how the battlefield splits.</p>

<table>
  <tr>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">DeepSeek-v3</strong><br/>
      <img src="assets/agent-growth_deepseek.gif" alt="DeepSeek-v3 Attack Replay" width="400" /><br/>
      <em>The baseline shows steady growth, while the attacked version declines almost monotonically.</em>
    </td>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Claude-4.5-Sonnet</strong><br/>
      <img src="assets/agent-growth_claude.gif" alt="Claude-4.5-Sonnet Attack Replay" width="400" /><br/>
      <em>The attacked version surged ahead initially, only to wipe out all gains in a sudden crash at the end.</em>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Qwen3-Max</strong><br/>
      <img src="assets/agent-growth_qwen.gif" alt="Qwen3-Max Attack Replay" width="400" /><br/>
      <em>The baseline remains flat, while the reverse-expectation attack triggers a steep profit surge.</em>
    </td>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Gemini 2.5 Flash</strong><br/>
      <img src="assets/agent-growth_gemini.gif" alt="Gemini 2.5 Flash Attack Replay" width="400" /><br/>
      <em>From the opening bell, the attacked curve diverges from baseline and the gap widens persistently.</em>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" colspan="2">
      <strong style="font-size: 22px;">GPT-5</strong><br/>
      <img src="assets/agent-growth_gpt.gif" alt="GPT-5 Attack Replay" width="400" /><br/>
      <em>The baseline rises steadily without clear cause, while the perturbed run behaves like a random walk.</em>
    </td>
  </tr>
</table>

---

>Experiments were specifically conducted on two types of attacks: "reverse expectation injection" and "fake news shockwave" with significant results, with the detailed walkthrough below focused on the `deepseek-v3` model.


<div align="center" style="margin-bottom: 20px;">
  <strong style="font-size: 20px;">Reverse Expectations Injection</strong><br/>
  <img src="assets/attack_with_reverse_expectations.png" alt="Reverse Expectation Attack" width="640" /><br/>
  <em>The poisoned reasoning trace pushes the planner to fight its own positions.</em>
</div>

<div align="center" style="margin-bottom: 20px;">
  <img src="assets/zoomed_asset_graph_with_reverse_expectations.png" alt="Reverse Expectation Telemetry" width="640" /><br/>
  <em>The poisoned prompt keeps doubling down on losing positions and cashing out early, so every rally stalls into a crash.</em>
</div>

---

<div align="center" style="margin-bottom: 20px;">
  <strong style="font-size: 20px;">Fake News Shockwave</strong><br/>
  <img src="assets/attack_with_fake_news.png" alt="Fake News Attack" width="640" /><br/>
  <em>Fabricated headlines drive the toolchain into a wave of panic adjustments.</em>
</div>

<div align="center" style="margin-bottom: 20px;">
  <img src="assets/zoomed_asset_graph_with_fake_news.png" alt="Fake News Telemetry" width="640" /><br/>
  <em>The staged “good news” inflates expectations, the agent commits heavily, and the book collapses on impact.</em>
</div>




---

## Payload Roadmap Checklist
Infrastructure
- [x] Integrated trading-agent platform combining core capabilities from mainstream stacks
- [x] Simple attack interfaces for rapid experimentation
- [x] Lightweight plugin system for extending payloads
- [ ] Adaptable to more trading platforms (e.g., NoFX, ValueCell)

Attack capabilities (delivered and planned)

- [x] Direct prompt injection — force catastrophic strategy pivots
- [x] MCP tool hijacking — let polluted data drive wrong decisions
- [ ] Data forgery (indirect prompt injection) — spark panic selling and irrational buying
- [ ] Model backdoors — hidden triggers to drain assets on demand
- [ ] Malicious collusion — compromised sub-agents twisting collective choices
- [ ] Memory poisoning — corrupt learned experiences to force strategy drift
- [ ] State tampering — induce cognitive confusion to desync from real positions
- [ ] Latency / DoS shocks — block exits, freeze hedges, let losses run
- [ ] Tool misuse — execute rogue orders to breach risk and compliance hard limits
---

## 🎭 What’s new Inside This Repo

<div align="center" style="margin: 24px 0;">
  <img src="assets/repo_frame.png" alt="Repository Structure Overview" width="500" />
</div>

**MCP hijacking layout**

```bash
├── agent_tools
│   ├── start_mcp_services.py
│   ├── tool_alphavantage_news.py
│   ├── tool_get_price_local.py
│   ├── tool_jina_search.py
│   ├── tool_math.py
│   ├── tool_trade.py
│   └── fake_agent_tools
│       ├── start_fake_mcp_services.py
│       └── ...
```

**Prompt-injection layout**

```bash
├── agent
│   ├── base_agent
│   │   ├── base_agent_hour.py
│   │   └── base_agent.py
│   ├── base_agent_astock
│   │   └── base_agent_astock.py
│   └── plugins
│       ├── prompt_injection_agent_hour.py   # hourly injections
│       ├── prompt_injection_agent.py        # daily injections
│       └── prompt_injection_manager.py      # rule matching
├── prompts
│   └── prompt_injections.json               # injection payloads
```
---

## 🔧 Operational Steps Example

### Start the AI-Trader core stack
```bash
# 1. Clone the repository and install dependencies
git clone https://github.com/TradeTrap/Safe-TradingAgent.git
cd Safe-TradingAgent/AI-Trader
pip install -r requirements.txt

# 2. Launch the official MCP services and capture a clean signature
cd agent_tools
python start_mcp_services.py &
cd ..
python main.py --signature clean-run
```

### Run the MCP hijacking scenario
```bash
#  Switch to the fake services and replay the compromised signature
cd agent_tools/fake_tool
python start_fake_mcp_services.py
cd ../..
python main.py --signature corrupted-run

# Review the recordings in the browser dashboard
cd agent_viewer
python3 -m http.server 8000
# Open http://localhost:8000 and compare the signatures
```

### Run the prompt-injection scenario
- Enable the prompt-injection agent:
  - Set `agent_type` to `PromptInjectionAgent` (or `PromptInjectionAgent_Hour`) in `configs/my_config.json`.
  - Add or enable the desired rules inside `prompts/prompt_injections.json`.
- Execute the experiment:
  ```bash
  python main.py --config configs/my_config.json --signature gemini-2.5-flash-with-injection
  ```
- Example registry excerpt for reference:
  ```bash
  AGENT_REGISTRY = {
      "BaseAgent": {
          "module": "agent.base_agent.base_agent",
          "class": "BaseAgent"
      },
      "BaseAgent_Hour": {
          "module": "agent.base_agent.base_agent_hour",
          "class": "BaseAgent_Hour"
      },
      "BaseAgentAStock": {
          "module": "agent.base_agent_astock.base_agent_astock",
          "class": "BaseAgentAStock"
      },
      "PromptInjectionAgent": {
          "module": "agent.plugins.prompt_injection_agent",
          "class": "PromptInjectionAgent"
      },
      "PromptInjectionAgent_Hour": {
          "module": "agent.plugins.prompt_injection_agent_hour",
          "class": "PromptInjectionAgentHour"
      }
  }
  ```


---
## 🙏 Acknowledgements

This project is inspired by the [AI-Trader](https://github.com/HKUDS/AI-Trader) project. We hereby express our gratitude for their pioneering work!

Building upon the original project, we focus on security research and attack scenario testing, providing tool support for the robust research of AI trading systems.


## ⚖️ Usage Guidelines

> This project exists to surface the risks hidden inside today’s trading agents.  
> Always run experiments in controlled environments; do not deploy or weaponise them in live markets.  
> Every reproduced case feeds back into discussions and improvements around defensive measures.

---

## 📄 License

Apache 2.0 © TradeTrap team — because even disruptive research should stay open-source.

---

<div align="center">

🧨 TradeTrap: Are LLM-based Trading Agents Truly Reliable and Faithful?
</div>
