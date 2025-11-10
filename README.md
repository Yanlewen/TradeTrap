<div align="center">

# 🧨 Trap Lab — Make Markets Bleed.


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
  <a href="README.zh.md" style="color: gray; text-decoration: none; padding: 0 12px;">中文</a>
</div>


A single malicious instruction can topple an entire fund — why stay on defense?
---

</div>

---

## ⚠️ One Tweak. Total Collapse.

> We changed a single line of code and slipped in a prompt that told the agent to act against its own plan. Within minutes the equity curve shot upward, then plunged; some base models failed immediately, others rallied before collapsing. One seemingly harmless injection was enough to trigger a chain of bad decisions and erase the account — this wasn’t variance, it was a deliberate trap.


<div align="center">
  <strong>Multi-Model Breakdown Under Identical Exploits</strong><br/>
  <img src="assets/final_assets_from_positions.png" alt="All Models Exploit Overview" width="880" />
</div>

<p align="center" style="margin: 40px 0 12px; rgb(5, 6, 6);">
Each GIF below drills into a single base model, comparing baseline behaviour, news-enhanced runs, and the exploited variant side by side.
</p>
<table>
  <tr>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">DeepSeek-v3</strong><br/>
      <img src="assets/agent-growth_deepseek.gif" alt="DeepSeek-v3 Attack Replay" width="400" /><br/>
      <em>Baseline steadily climbs; the poisoned version drifts downward and quietly eats the gains.</em>
    </td>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Claude-4.5-Sonnet</strong><br/>
      <img src="assets/agent-growth_claude.gif" alt="Claude-4.5-Sonnet Attack Replay" width="400" /><br/>
      <em>The attack lands late — the curve surges first, then crashes even harder at the end.</em>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Qwen3-Max</strong><br/>
      <img src="assets/agent-growth_qwen.gif" alt="Qwen3-Max Attack Replay" width="400" /><br/>
      <em>Amplified volatility spreads the contamination across the entire run.</em>
    </td>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Gemini 2.5 Flash</strong><br/>
      <img src="assets/agent-growth_gemini.gif" alt="Gemini 2.5 Flash Attack Replay" width="400" /><br/>
      <em>Latency in the toolchain snowballs into a run of misfires.</em>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">GPT-5</strong><br/>
      <img src="assets/agent-growth_gpt.gif" alt="GPT-5 Attack Replay" width="400" /><br/>
      <em>Holds up briefly before the prompt hijack drags it into a plunge.</em>
    </td>
    <td align="center" valign="top" width="50%">
      &nbsp;
    </td>
  </tr>
</table>

> The same attack script behaves differently across base models, but the outcome is identical: profits disappear fast. No matter how polished the agent looks, one poisoned signal can wipe out double-digit gains in seconds — relying blindly on automated trading is a high-risk bet.

---
## 🧬 Why Our Attack Works

Most trading agents already carry structural weaknesses:
- ⚡ A minor tweak can push the strategy off a cliff.
- 🧩 They are highly sensitive to external noise, so outcomes swing wildly.
- 💀 There is little stability assurance; capital buffers collapse without warning.
- 🎭 Decisions are black boxes, so you rarely know where the loss came from.

Target those weak spots and the system destabilises quickly: a warped model response, an injected signal, or a polluted API call is enough to make an otherwise steady agent unravel.

The two experiment sets below show how reverse expectations and fake news injections turn these latent weaknesses into visible failures.

<div align="center" style="margin: 32px 0;">
  <span style="font-size: 18px; font-weight: 600; color: #6c7b94;">— Two different security attack methods —</span>
</div>
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

> Two signatures, two tailored payloads, the same profit wipeout:
> - Reverse expectations rewires the planner’s logic and turns long positions into self-sabotage.
> - Fake news hijacks external sentiment, pushes the agent to chase phantom opportunities, and dumps the book.
>
> Reproduce both attacks with the provided scripts, review the logs, and adapt the payloads to suit your own investigations.
---

## 💣 From Safe Room to Test Range

> Automated trading agents are being mythologised as “money printers,” and the herd mentality is dangerous for individuals and markets alike.  
> Believing you’re still sitting safely behind guarded walls is the biggest risk — we have to go on the offensive to spot the cracks.  
> This project is a live-fire range: map every layer, document the failures, and only then can real hardening begin.

- 💉 **Signal poisoning**: Feed malicious market data and measure how fast the strategy degrades.
- 🧠 **Prompt hijacking**: Force the planner to undermine its own logic.
- 🧱 **Sandbox escapes**: Break isolation, seize the toolchain, rewrite the rules.

We surface the weak spots so you can reproduce, analyse, and close them.


---

## Potential Attack Surfaces in Financial Trading
<div align="center">
  <img src="assets/frame.png" alt="Attack Surface Frame" width="820" />
</div>

- **Sense layer**  
  - Data forgery (indirect prompt injection) → panic sell-offs alternating with irrational buying.  
  - MCP tool hijacking → polluted tool outputs steer the strategy toward failure.

- **Planning layer**  
  - Direct prompt injection → forced liquidations and sudden strategic flips.  
  - Model backdoors → dormant triggers siphon assets on command.  
  - Malicious collusion → compromised sub-agents distort shared conclusions.

- **Execution layer**  
  - Latency floods / DoS → missed exits, frozen hedges, uncontrolled drawdowns.

- **Custody layer**  
  - API credential theft → account balances disappear instantly.  
  - Private key exfiltration → crypto holdings evaporate overnight.  
  - Smart-contract kill switches → assets get frozen or rerouted.

- **Memory layer**  
  - In planning: long-horizon memory poisoning and narrative manipulation.

---

## 🎯 Mission Status

**Resources available today**
- Baseline poisoning scripts to reproduce the major failure modes.
- Attack replays and step-by-step guides to accelerate onboarding.

---

### Payload Roadmap Checklist
**Infrastructure**
- [x] Integrated trading-agent platform combining core capabilities from mainstream stacks
- [x] Simple attack interfaces for rapid experimentation
- [x] Lightweight plugin system for extending payloads

**Attack capabilities (delivered and planned)**
- [x] Direct prompt injection — force catastrophic strategy pivots
- [x] MCP tool hijacking — let polluted data drive wrong decisions
- [ ] Data forgery (indirect prompt injection) — spark panic selling and irrational buying
- [ ] Model backdoors — hidden triggers to drain assets on demand
- [ ] Malicious collusion — compromised sub-agents twisting collective choices
- [ ] Latency / DoS shocks — block exits, freeze hedges, let losses run
- [ ] API credential theft — drain account balances without notice
- [ ] Private key exfiltration — empty crypto reserves overnight
- [ ] Smart-contract kill switches — freeze or reroute asset flows

---

## 🎭 What’s Inside This Repo

| Vault | Assets you can use |
| --- | --- |
| `AI-Trader/agent_tools/fake_tool/` | Port-hijacking impostor services for prices, news, X, and Reddit — swap in forged realities without touching agent code. |
| `AI-Trader/news_data/` | Full transcripts of every external call — timestamps, payloads, injected flags. Perfect ammo for forensic bragging rights. |
| `AI-Trader/agent_viewer/` | Browser dashboard to replay the meltdown in living color, comparing clean vs. corrupted signatures side-by-side. |
| `AI-Trader/data/agent_data/` | Raw experiment traces, equity curves, execution logs — clone them, corrupt them, narrate the downfall. |
| `AI-Trader/prompts/` | Prebaked prompt hooks and injection slots so you can whisper treason straight into the planner’s ear. |
| `SIGNATURE_FIX_README.md` | Casefile of prior breaches and containment attempts — study, replicate, extend. |

Treat these components as building blocks for your own evaluations.

---

## 🔧 Operational Steps Example

```bash
# 1. Clone the repository and install dependencies
git clone https://github.com/your-org/Safe-TradingAgent.git
cd Safe-TradingAgent/AI-Trader
pip install -r requirements.txt

# 2. Start the standard services and record a baseline run
cd agent_tools
python start_mcp_services.py &
cd ..
python main.py --signature clean-run

# 3. Start the fake services and run the compromised scenario
cd agent_tools/fake_tool
python start_fake_mcp_services.py
cd ../..
python main.py --signature corrupted-run

# 4. Review the visualised results
cd agent_viewer
python3 -m http.server 8000
# Visit http://localhost:8000 to compare the signatures
```

If you prefer notebooks, connect to the same data streams and fake services under `AI-Trader/` and run the experiments interactively.

---

## 🧪 Scenarios Ready For You (Right Now)

- **Price Crash Puppet** — Forge price candles via `fake_price_service.py` and watch the portfolio crater on command.
- **Headline Hallucination** — Inject weaponized “breaking news” with `fake_search_service.py` plus custom prompt inserts.
- **Sentiment Siren** — Bend social buzz through `fake_x_service.py` and `fake_reddit_service.py`, then follow the herd off the cliff.
- **Prompt Possession** — Slip malicious post-tool prompts from `prompts/post_news_injections.json` to rewrite the agent’s moral compass mid-run.

We welcome additional scenarios — fork the project, open a PR, or share a reproducible report.

## 🛠️ Product Overview — Trap Lab

- 🎯 **Clear positioning**: A reproducible, extensible testbed for attacking and defending trading agents.
- 🧩 **Complete modules**: Real/fake services, logging, visualisation, and replay — ready out of the box.
- 🔐 **Open boundaries**: Low-friction interfaces so teams can iterate on new attack or defence capabilities quickly.
- 🚀 **Focused outputs**: Verified vulnerability examples and reproduction steps that inform security hardening.

The goal isn’t “perfect safety” today, but continuous evidence gathering that drives the next generation of resilient financial AI systems.

---

## ⚖️ Usage Guidelines

> This project exists to surface the risks hidden inside today’s trading agents.  
> Always run experiments in controlled environments; do not deploy or weaponise them in live markets.  
> Every reproduced case feeds back into discussions and improvements around defensive measures.

---

## 📄 License

Apache 2.0 © xxx team — because even disruptive research should stay open-source.

---

<div align="center">

💥 Trap Lab — Make Markets Bleed.
</div>

