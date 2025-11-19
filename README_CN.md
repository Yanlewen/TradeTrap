<div align="center">
<h1 style="margin: 0; display: inline-flex; align-items: center; gap: 12px;">
  <span> 🧨  TradeTrap: Are LLM-based Trading Agents Truly Reliable and Faithful?</span>
</h1>

<div align="center" style="line-height: 2; margin: 16px 0 18px;">
    <a href="https://www.python.org/downloads" target="_blank">
        <img src="https://img.shields.io/badge/python-3.10+-blue.svg"
            alt="Python version"></a>
    <a href="LICENSE" target="_blank">
        <img src="https://img.shields.io/badge/license-Apache2.0-red.svg"
            alt="License: Apache2.0"></a>  
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-999999.svg"
         alt="Platform: macOS | Linux">

    
</div>

<div align="center" style="margin-top: 2px; gap: 20px; display: inline-flex;">
  <a href="README.md" style="color: auto; text-decoration: none; padding: 0 12px;">English</a>
  <a href="README.zh.md" style="color: gray; text-decoration: none; padding: 0 12px;">中文</a>
</div>


---
**TradeTrap**是一个由社区驱动且对开发者友好的工具，用于测试基于大语言模型（LLM）的交易代理的可靠性。对基于大语言模型的代理的输入指令稍作干扰，就可能颠覆整个投资方案！因此，我们的使命是建立可靠的金融代理社区。欢迎分享您遇到的反馈和问题，并邀请更多开发者参与贡献 🚀🚀🚀
</div>
<div align="center">
  <strong>多基座模型同场攻击表现对比</strong><br/>
  <img src="assets/final_assets_from_positions.png" alt="多模型攻击对比" width="880" />
  
</div>


## 金融交易场景的潜在脆弱点
<div align="center">
  <img src="assets/frame.jpeg" alt="攻击面分层示意图" width="820" />
</div>

- **市场情报**  
  - 数据伪造（间接提示注入）→ 恐慌抛售与非理性抢购。
  - MCP 工具劫持 → 数据源被替换/污染。

- **策略制定**  
  - 直接提示注入 → 错误决策，强制清仓与爆仓。
  - 模型后门 → 隐藏触发器随时损害资产。
  - 恶意协同 → 恶意的sub-agents误导共享决策。

- **持仓与台账**  
  - 内存投毒 → 策略偏移会导致模型学习错误的经验。
  - 状态篡改 → 对自身持仓/订单状态的认知混乱。

- **交易执行**  
  - 延迟洪水 / DoS → 错失时机，无法止损/平仓。
  - 工具误用 → 执行非预期指令、违反风险/合规规则。

---


## 🛠️ 我们的TradeTrap能做什么

我们的仓库提供了一系列即插即用的攻击模块，可直接集成到AI-Trader平台中。这些插件能够在LLM交易智能体运行时进行主动干扰，让您通过以下两种主要攻击向量测试其鲁棒性：

- 🪂提示词注入

  - 逆向预期：反转智能体对市场信号的解读，使其在熊市条件下做多，在牛市环境下做空。

  - 篡改结果：伪造智能体接收的历史或模拟交易结果数据，使其基于虚假的过往表现做出错误的策略调整。

- 🛠️MCP工具劫持
    - 接管智能体的外部数据源——如价格流、新闻API或社交情绪工具——用精心构造的虚假数据流替代真实信息，从而引导其决策偏离正轨。


例如：

下面的五组实验逐一剖开不同LLM agent在「无工具 / 正常新闻 / 投毒场景」下的轨迹，让脆弱性变得可见且可复现。


<div align="center" style="margin-bottom: 24px;">
  <img src="assets/agent-legend.png" alt="Agent Comparison Legend" width="600" />
</div>
<p align="center" style="font-size: 10px; margin: -48px 0 24px; line-height: 1.6;">
<div align="center" style="margin: 12px 0 6px; font-size: 13px; line-height: 1.7; font-weight: 500;">
  🟨 <strong>黄色</strong>：不接入任何外部信号的基线策略。<br/>
  🔵 <strong>蓝色</strong>：接入 X/Twitter 与 Reddit 新闻流后的增强策略。<br/>
  🔴 <strong>红色</strong>：在相同初始资金下运行的攻击版本。
</div>

<p align="center" style="margin: 0 0 18px; font-style: italic; font-size: 12px;">全部从 5,000 美元起步，看不同路线如何迅速分化。</span></p>

<table>
  <tr>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">DeepSeek-v3</strong><br/>
      <img src="assets/agent-growth_deepseek.gif" alt="DeepSeek-v3 攻击复现" width="400" /><br/>
      <em>基准线稳步攀升，而遭受攻击后曲线几乎呈单边下跌。</em>
    </td>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Claude-4.5-Sonnet</strong><br/>
      <img src="assets/agent-growth_claude.gif" alt="Claude-4.5-Sonnet 攻击复现" width="400" /><br/>
      <em>受攻击版本一度大幅领先，却在交易末期利润尽数回吐，迅速崩盘。</em>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Qwen3-Max</strong><br/>
      <img src="assets/agent-growth_qwen.gif" alt="Qwen3-Max 攻击复现" width="400" /><br/>
      <em>基准线持续低迷，而反预期攻击却使其收益曲线陡峭上扬。</em>
    </td>
    <td align="center" valign="top" width="50%">
      <strong style="font-size: 22px;">Gemini 2.5 Flash</strong><br/>
      <img src="assets/agent-growth_gemini.gif" alt="Gemini 2.5 Flash 攻击复现" width="400" /><br/>
      <em>从开盘起，受攻击曲线便与基准线分道扬镳，差距持续扩大。</em>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" colspan="2">
      <strong style="font-size: 22px;">GPT-5</strong><br/>
      <img src="assets/agent-growth_gpt.gif" alt="GPT-5 攻击复现" width="400" /><br/>
      <em>基准线无故持续飙升，而被干扰的运行则表现得如同随机游走。</em>
    </td>
  </tr>
</table>


>专门针对两种攻击类型进行了展开分析：“反向预期注入”和“假新闻冲击”，并取得了显著成果，下面的详细步骤说明将重点介绍`deepseek-v3`模型。


<div align="center" style="margin-bottom: 20px;">
  <strong style="font-size: 20px;">逆向预期注入</strong><br/>
  <img src="assets/attack_with_reverse_expectations.png" alt="逆向预期攻击" width="640" /><br/>
  <em>被污染的推理链逼迫智能体与自己作对。</em>
</div>

<div align="center" style="margin-bottom: 20px;">
  <img src="assets/zoomed_asset_graph_with_reverse_expectations.png" alt="逆向预期细节" width="640" /><br/>
  <em>被污染后的推理不断加仓亏损资产、过早止盈，反弹一次次夭折。</em>
</div>

---

<div align="center" style="margin-bottom: 20px;">
  <strong style="font-size: 20px;">假新闻冲击</strong><br/>
  <img src="assets/attack_with_fake_news.png" alt="假新闻攻击" width="640" /><br/>
  <em>伪造头条引爆工具链的恐慌调整。</em>
</div>

<div align="center" style="margin-bottom: 20px;">
  <img src="assets/zoomed_asset_graph_with_fake_news.png" alt="假新闻细节" width="640" /><br/>
  <em>虚假利好把预期吹到天花板，模型盲信后重仓下注，结果轰然垮塌。</em>
</div>


---

## 最新更新

- **状态篡改插件**：通过篡改智能体对持仓状态的认知来操纵交易智能体。详见 [`plugins/README_zh.md`](plugins/README_zh.md) ([English](plugins/README.md))。

---

## 🎯 任务进度

**基础设施**
- [x] 完整的交易 agent 平台（融合主流交易智能体的核心功能）
- [x] 简单易用的攻击接口
- [x] 轻量化攻击插件体系
- [x] 适配更多交易平台（如 NoFX、ValueCell）

**攻击能力（已交付与规划）**
- [x] 直接提示注入 —— 强迫策略做出灾难性转向
- [x] MCP 工具劫持 —— 让污染数据驱动错误决策
- [ ] 记忆投毒 —— 破坏获得的经验以迫使策略偏离
- [x] 状态篡改 —— 引发认知混乱，从而与实际位置不同步
- [ ] 数据伪造（间接提示注入）—— 引爆恐慌抛售与非理性扫货
- [ ] 模型后门 —— 隐藏触发器，一声令下掏空资产
- [ ] 恶意协同 —— 被攻陷的子智能体扭曲群体决策

- [ ] 延迟 / DoS 冲击 —— 阻断止损、冻结对冲，让亏损持续扩大
- [ ] 工具误用 —— 执行违规指令，突破风险与合规的硬性限制

---

## 🎭 仓库里面有什么

<div align="center" style="margin: 24px 0;">
  <img src="assets/repo_frame.png" alt="仓库结构概览" width="500" />
</div>

**MCP 劫持目录结构**

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

**提示词注入目录结构**

```bash
├── agent
│   ├── base_agent
│   │   ├── base_agent_hour.py
│   │   └── base_agent.py
│   ├── base_agent_astock
│   │   └── base_agent_astock.py
│   └── plugins
│       ├── prompt_injection_agent_hour.py   # 小时级注入
│       ├── prompt_injection_agent.py        # 日级注入
│       └── prompt_injection_manager.py      # 规则匹配
├── prompts
│   └── prompt_injections.json               # 注入负载
```

---

## 🔧 操作步骤示例

### 1. 环境设置
```bash
# 克隆仓库
git clone https://github.com/TradeTrap/Safe-TradingAgent.git
cd Safe-TradingAgent

# 安装依赖（统一的 requirements.txt 在根目录）
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 并填入您的 API 密钥（OPENAI_API_KEY、TUSHARE_TOKEN 等）
```

### 2. 选择目标：AI-Trader 或 Valuecell

TradeTrap 支持测试两种不同的交易智能体实现。根据您的测试需求选择其一：

#### 选项 A：运行 AI-Trader
AI-Trader 是集成了 MCP（Model Context Protocol）的原始交易智能体。

```bash
# 1. 启动官方 MCP 服务（AI-Trader 必需）
cd AI-Trader/agent_tools
python start_mcp_services.py &
cd ../..

# 2. 使用配置文件运行 AI-Trader
python main.py configs/default_config.json
# 或使用其他 AI-Trader 配置：
# python main.py configs/default_astock_config.json  # A股市场
# python main.py configs/default_crypto_config.json # 加密货币市场
```

**可用的 AI-Trader agent 类型：**
- `BaseAgent` - 标准交易智能体
- `BaseAgent_Hour` - 小时级交易智能体
- `BaseAgentAStock` - A股市场智能体
- `BaseAgentCrypto` - 加密货币智能体
- `PromptInjectionAgent` - 用于提示词注入测试
- `PositionAttackAgent_Hour` - 用于持仓攻击测试

#### 选项 B：运行 Valuecell
Valuecell 是一个独立的自动交易智能体，内置技术分析和投资组合管理功能。

```bash
# Valuecell 不需要 MCP 服务，直接运行：
python main.py configs/valuecell_config.json
# 或使用其他 valuecell 配置：
# python main.py configs/default_auto_trading_standalone_config.json  # 加密货币
# python main.py configs/default_auto_trading_stock_config.json        # 股票
```

**Valuecell agent 类型：**
- `Valuecell` - 支持股票和加密货币市场的统一智能体

### 3. 运行攻击场景

TradeTrap 支持多种攻击场景来测试智能体的可靠性：

- **MCP 劫持**：测试智能体如何响应被操纵的外部数据
  - 参见：[`AI-Trader/agent_tools/fake_tool/README.md`](AI-Trader/agent_tools/fake_tool/README.md)

- **状态篡改攻击**：测试智能体如何处理被篡改的持仓状态信息
  - 通过 `LD_PRELOAD` 使用文件钩子在运行时拦截并修改智能体读取的持仓数据
  - 使智能体基于错误的状态认知做出交易决策，而实际账本保持不变
  - 参见：[`plugins/README.md`](plugins/README.md) 了解详细使用说明

- **插件攻击模块**：`AI-Trader/agent/plugins/` 目录包含多个攻击插件，可用于测试智能体漏洞：
  - **提示词注入**：测试智能体如何处理注入到决策过程中的对抗性提示
  - **持仓攻击**：测试智能体如何处理修改交易历史的被篡改持仓记录
  - 参见：[`AI-Trader/agent/plugins/README.md`](AI-Trader/agent/plugins/README.md) 了解详细使用说明



---
## 🙏 致谢

本项目受到 [AI-Trader](https://github.com/HKUDS/AI-Trader) 项目启发，特此感谢他们的开源工作！

感谢以下开源项目和服务：
- [AI-Trader](https://github.com/HKUDS/AI-Trader) - 自主交易agent框架
- [LangChain](https://github.com/langchain-ai/langchain) - AI应用开发框架
- [MCP](https://github.com/modelcontextprotocol) - Model Context Protocol
- [Alpha Vantage](https://www.alphavantage.co/) - 美股金融数据API
- [Tushare](https://tushare.pro/) - A股市场数据API
- [Jina AI](https://jina.ai/) - 信息搜索服务

## 👥 管理员

<div align="center">

<a href="https://github.com/Yanlewen">
  <img src="https://avatars.githubusercontent.com/Yanlewen?v=4" width="80" height="80" alt="TianyuFan0504" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/mjl0613ddm">
  <img src="https://avatars.githubusercontent.com/mjl0613ddm?v=4" width="80" height="80" alt="yangqin-jiang" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/amandajshao">
  <img src="https://avatars.githubusercontent.com/amandajshao?v=4" width="80" height="80" alt="yuh-yang" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/shenqildr">
  <img src="https://avatars.githubusercontent.com/shenqildr?v=4" width="80" height="80" alt="Hoder-zyf" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/EaKal-7">
  <img src="https://avatars.githubusercontent.com/EaKal-7?v=4" width="80" height="80" alt="Hoder-zyf" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/tmylla">
  <img src="https://avatars.githubusercontent.com/tmylla?v=4" width="80" height="80" alt="Hoder-zyf" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/titanwings">
  <img src="https://avatars.githubusercontent.com/titanwings?v=4" width="80" height="80" alt="Hoder-zyf" style="border-radius: 50%; margin: 5px;"/>
</a>






## ⚖️ 使用须知

> 该项目旨在揭示当前交易智能体的潜在风险。  
> 请务必在可控环境中使用，避免在真实市场直接部署或武器化。  
> 所有复现案例会用于推进安全防护的讨论与改进。

---


## 📄 许可证

Apache 2.0 © TradeTrap 团队
