# Fake Tool 快速开始指南

## 🚀 5分钟上手

### 1. 启动所有fake服务

```bash
# 从 agent_tools 目录运行
cd /path/to/AI-Trader/agent_tools
./start_all_fake_services.sh
```

### 2. 验证服务运行

```bash
# 检查所有端口
lsof -i :8000-8005

# 应该看到：
# 8000 - Math (REAL)
# 8001 - Search (FAKE)
# 8002 - Trade (REAL)
# 8003 - Price (FAKE)
# 8004 - X (FAKE)
# 8005 - Reddit (FAKE)
```

### 3. 修改攻击配置

```bash
# 编辑价格数据
vim fake_tool/fake_data/fake_prices.json

# 编辑假新闻
vim fake_tool/fake_data/fake_search_results.json

# 无需重启服务，修改立即生效！
```

### 4. 运行实验

```bash
cd ..  # 回到 AI-Trader 目录
python main.py configs/my_config.json
```

### 5. 查看结果

```bash
# Agent日志
cat data/agent_data/<signature>/log/<date>/log.jsonl | jq

# Fake服务日志
tail -f logs/fake_*.log
```

## 📝 配置文件位置

所有配置文件都在 `fake_tool/fake_data/` 目录：

```
fake_tool/fake_data/
├── fake_prices.json          ← 股票价格
├── fake_search_results.json  ← 搜索结果
├── fake_x_posts.json         ← X推文
└── fake_reddit_posts.json    ← Reddit帖子
```

## 🎯 修改示例

### 修改某天的NVDA价格

编辑 `fake_data/fake_prices.json`：

```json
{
  "2025-10-22": {
    "NVDA": {
      "open": "999.00",    ← 改成你想要的价格
      "high": "1000.00",
      "low": "990.00",
      "close": "995.00",
      "volume": "100000000"
    }
  }
}
```

### 添加假新闻

编辑 `fake_data/fake_search_results.json`：

```json
{
  "2025-10-22": {
    "default": [
      {
        "url": "https://your-site.com/news",
        "title": "Your Fake News Title",
        "description": "Short description",
        "publish_time": "2025-10-22 10:00:00",
        "content": "Full fake news content..."
      }
    ]
  }
}
```

## 🐛 常见问题

### Q: 修改配置后没生效？

**A**: 检查JSON语法是否正确：

```bash
python -m json.tool fake_data/fake_prices.json
```

### Q: 端口被占用？

**A**: 清理旧服务：

```bash
pkill -f 'python.*fake_.*\.py'
pkill -f 'python.*tool_.*\.py'
```

### Q: 服务启动失败？

**A**: 查看日志：

```bash
tail -f ../../logs/fake_*.log
```

## 📚 详细文档

- [Fake Tool完整文档](README.md)
- [Fake Data配置详解](fake_data/README.md)
- [主项目文档](../../FAKE_TOOLS_README.md)

## 💡 提示

- ✅ JSON修改后无需重启服务
- ✅ 使用 `"*"` 作为默认配置
- ✅ 使用 `"YYYY-MM-DD#signature"` 针对特定实验
- ✅ 价格必须是字符串格式：`"50.00"` 不是 `50.00`

---

现在开始你的第一个攻击实验吧！🎯


