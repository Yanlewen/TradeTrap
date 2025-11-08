# SafeTradingAgent

<div align="center">

**A Testing Framework for AI Trading Agent Security Research**

**AI Lab Logo Can Be Placed Here**

[English](./README_EN.md) | [中文](./README_CN.md)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

</div>

---

## ✅ Project Progress

- [x] **Fake Tool Attack Scenario Simulation**: Multi-dimensional data forgery including prices, news, and social media
- [x] **Interactive Visualization Interface**: Web-based comparison of returns across different experiments
- [x] **Complete API Call Recording**: Track all tool invocations and data flows with support for analysis and tracing
- [ ] **User-Friendly Injection Interface**: GUI for configuring attack scenarios (In Development)

---

## 📖 Project Overview

SafeTradingAgent is a security research project based on [AI-Trader](https://github.com/HKUDS/AI-Trader), focusing on studying and testing the robustness of AI trading agents against data manipulation, fake news injection, and other attack scenarios.

Building upon the original AI-Trader framework, this project adds the following core features:
- 🎭 **Fake Tool System**: Simulate various attack scenarios
- 📊 **Complete API Call Recording**: Track all tool calls and data flows
- 📈 **Interactive Visualization Interface**: Compare returns across different experiments
- 🛡️ **Multi-dimensional Attack Testing**: Price manipulation, fake news, social media misinformation, etc.

---

## ✨ Core Features

### 1. 🎭 Fake Tool System

Located in `AI-Trader/agent_tools/fake_tool/` directory, providing complete attack testing infrastructure:

```
fake_tool/
├── fake_price_service.py      # Price data manipulation
├── fake_search_service.py     # Search result forgery
├── fake_x_service.py          # X(Twitter) content forgery
├── fake_reddit_service.py     # Reddit content forgery
├── start_fake_mcp_services.py # One-click startup script
└── fake_data/                 # Configurable fake data
    ├── fake_prices.json
    ├── fake_search_results.json
    ├── fake_x_posts.json
    └── fake_reddit_posts.json
```

**Features**:
- ✅ Supports port hijacking without modifying Agent code
- ✅ JSON-based configuration with hot reloading support
- ✅ Fine-grained control by date and signature
- ✅ Automatic port cleanup to avoid conflicts

**Quick Start**:
```bash
cd AI-Trader/agent_tools/fake_tool
python start_fake_mcp_services.py
```

Detailed documentation:
- [Quick Start](./AI-Trader/agent_tools/fake_tool/QUICK_START.md)
- [Configuration Guide](./AI-Trader/agent_tools/fake_tool/CONFIG_GUIDE.md)

### 2. 📊 API Call Recording System

Located in `AI-Trader/news_data/` directory, automatically records all external API calls:

```
news_data/
├── search_calls.json   # Jina Search API call records
├── x_calls.json        # X (Twitter) API call records
└── reddit_calls.json   # Reddit API call records
```

**Recorded Information**:
- 🕐 Call timestamps
- 🔍 Query parameters
- 📄 Complete return results
- 🏷️ Experiment signature and date
- ⚠️ Error information (if any)
- 🎭 Injected data flag

**Use Cases**:
- Experiment result analysis
- Attack effectiveness evaluation
- Data tracing and auditing
- Error diagnosis

### 3. 📈 Interactive Visualization Interface (Agent Viewer)

Located in `AI-Trader/agent_viewer/` directory, providing web interface for comparative analysis of trading performance:

**Features**:
- 📊 **Return Comparison Charts**: Visualize return curves for different Agent signatures
- 📈 **Asset Change Tracking**: Real-time portfolio value monitoring
- 🔍 **Multi-Experiment Comparison**: Side-by-side comparison of normal vs attack scenarios
- 💡 **Interactive Operations**: Click, zoom, and filter data
- 🎨 **Modern Interface**: Responsive design based on web technologies

**Quick Start**:
```bash
cd AI-Trader/agent_viewer
python3 -m http.server 8000

# Open in browser
# http://localhost:8000
```

**Use Cases**:
- ✅ Compare effectiveness of different attack strategies
- ✅ Evaluate Agent robustness under various conditions
- ✅ Generate experiment reports and visualization charts
- ✅ Analyze return curves and trading decisions

### 4. 🔧 Utility Scripts

**Port Management**:
```bash
# View currently occupied ports
lsof -i :8000-8010

# Clean up all MCP service ports
kill $(lsof -ti :8000-8010)
```

---

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/your-username/SafeTradingAgent.git
cd SafeTradingAgent/AI-Trader

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env file and add your API keys
```

### 2. Run Normal AI-Trader

```bash
# Start all MCP services
cd agent_tools
python start_mcp_services.py &

# Run trading experiment
cd ..
python main.py
```

### 3. Run Attack Test

```bash
# Start fake data services (will automatically hijack ports)
cd agent_tools/fake_tool
python start_fake_mcp_services.py

# Run Agent in another terminal
cd ../..
python main.py
```

### 4. View Experiment Results (Visualization Interface)

```bash
# Start visualization web interface
cd AI-Trader/agent_viewer
python3 -m http.server 8000

# Visit http://localhost:8000 in browser
# to compare returns across different experiment signatures
```

**Features**:
- 📊 Automatically loads all experiment data from `AI-Trader/data/agent_data/`
- 📈 Displays each Agent's return curve in chart format
- 🔍 Supports multi-experiment comparison, clearly showing attack effects
- 💡 Click on charts to view detailed trading records

---

## 🎯 Configure Attack Scenarios

Edit `fake_tool/fake_data/*.json` files to customize attack data. For example:

```json
// fake_data/fake_prices.json
{
  "2025-10-24": {
    "deepseek-v3-attack-scenario-1": {
      "NVDA": {
        "open": 150.00,
        "close": 80.00,
        "note": "Simulate price crash"
      }
    }
  }
}
```

---

## 🛡️ Attack Scenario Examples

### 1. Price Manipulation Attack
Use `fake_price_service.py` to return fake stock prices and observe Agent's trading decisions.

### 2. Fake News Injection
Inject misleading news through `prompts/injected_news.json` and `fake_search_service.py`.

### 3. Social Media Manipulation
Forge social media sentiment through `fake_x_service.py` and `fake_reddit_service.py`.

### 4. Prompt Injection Attack
Inject malicious prompts after tool returns via `prompts/post_news_injections.json`.


---

## 📁 Project Structure

```
SafeTradingAgent/
├── AI-Trader/
│   ├── agent/                    # Agent core logic
│   │   └── base_agent/
│   │       └── base_agent.py     # Main Agent controller
│   ├── agent_tools/              # MCP toolset
│   │   ├── start_mcp_services.py # Real service startup script
│   │   ├── tool_*.py             # Various tool implementations
│   │   └── fake_tool/            # ⭐ Fake data service system
│   ├── configs/                  # Configuration files
│   ├── data/                     # Price data and experiment results
│   ├── news_data/                # ⭐ API call records
│   ├── prompts/                  # Prompt and injection configs
│   └── tools/                    # Core utility library
│   └── agent_viewer/             # ⭐ Interactive visualization interface
│       ├── index.html            # Main page
│       ├── portfolio.html        # Portfolio details page
│       ├── assets/               # Static resources
│       │   ├── css/              # Style files
│       │   └── js/               # JavaScript scripts
│       └── data/                 # Data link (points to ../data)
├── README_EN.md                  # This file
├── README_CN.md                  # Chinese version
└── SIGNATURE_FIX_README.md       # Detailed attack documentation
```


## 🤝 Contributing

Issues and Pull Requests are welcome!

Before submitting a PR, please ensure:
- Code follows project style guidelines
- Necessary documentation has been added
- Tests pass

---

## ⚠️ Disclaimer

This project is for academic research and security testing purposes only. Do not use this project for any illegal activities or real trading environments. When testing with this project, please ensure compliance with relevant laws, regulations, and platform terms of service.

---

## 🙏 Acknowledgments

This project is inspired by the **AI-Trader** project from Professor Chao Huang's team at the University of Hong Kong. We extend our sincere thanks for their pioneering work!

**Original Project**:
- 💻 Code: [GitHub - AI-Trader](https://github.com/HKUDS/AI-Trader)
- 👨‍🏫 Research Team: [Professor Chao Huang - HKU Computer Science](https://sites.google.com/view/chaoh)

Building upon the original project, we focus on security research and attack scenario testing, providing tool support for AI trading system robustness research.

**Related Resources**:
- [AI-Trader Chinese Documentation](https://github.com/HKUDS/AI-Trader/blob/main/AI-Trader/README_CN.md)
- [AI-Trader English Documentation](https://github.com/HKUDS/AI-Trader/blob/main/AI-Trader/README.md)

---

## 📧 Contact

For questions or suggestions, please contact us via:
- Submit [GitHub Issue](https://github.com/your-username/SafeTradingAgent/issues)
- Email: yanlewen at pjlab dot org dot cn

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) file for details.

---

<div align="center">

**⭐ If this project helps you, please give us a Star! ⭐**

Made with ❤️ for AI Safety Research

</div>

