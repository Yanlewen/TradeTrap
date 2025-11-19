# 配置指南 Configuration Guide

## 📋 快速配置

打开 `start_fake_mcp_services.py`，找到第 347-361 行的配置区域：

```python
# ════════════════════════════════════════════════════════════════
# 🎯 Configuration - Modify these settings
# ════════════════════════════════════════════════════════════════

# Whether to start real Math and Trade services
# False = Only FAKE services (recommended, avoids port conflicts)
# True = Start both REAL and FAKE services
ENABLE_REAL_SERVICES = False  # ← 改这里！

# Custom port configuration (optional)
# None = Use default ports
# Or customize: {'price': 9003, 'search': 9001, 'x': 9004}
CUSTOM_PORTS = None  # ← 或自定义端口

# ════════════════════════════════════════════════════════════════
```

---

## 🎯 场景配置

### 场景 1: 纯 FAKE 服务测试（默认，推荐）

```python
ENABLE_REAL_SERVICES = False
CUSTOM_PORTS = None
```

**运行：**
```bash
python start_fake_mcp_services.py
```

**结果：**
- ⏸️  Math 服务：跳过
- ⏸️  Trade 服务：跳过
- ✅ FakeSearch：端口 8006
- ✅ FakePrices：端口 8008
- ✅ FakeXSearch：端口 8009
- ✅ FakeRedditSearch：端口 8010

---

### 场景 2: 完整服务（FAKE + REAL）

```python
ENABLE_REAL_SERVICES = True
CUSTOM_PORTS = None
```

**运行：**
```bash
python start_fake_mcp_services.py
```

**结果：**
- ✅ Math 服务：端口 8000
- ✅ Trade 服务：端口 8002
- ✅ FakeSearch：端口 8006
- ✅ FakePrices：端口 8008
- ✅ FakeXSearch：端口 8009
- ✅ FakeRedditSearch：端口 8010

**注意：** 确保端口 8000 和 8002 未被占用！

---

### 场景 3: 自定义端口 + 纯 FAKE

```python
ENABLE_REAL_SERVICES = False
CUSTOM_PORTS = {
    'price': 9003,
    'search': 9001,
    'x': 9004,
    'reddit': 9005
}
```

**运行：**
```bash
python start_fake_mcp_services.py
```

**结果：**
- ⏸️  Math 服务：跳过
- ⏸️  Trade 服务：跳过
- ✅ FakeSearch：端口 **9001**
- ✅ FakePrices：端口 **9003**
- ✅ FakeXSearch：端口 **9004**
- ✅ FakeRedditSearch：端口 **9005**

---

## 🔧 端口说明

### 默认端口分配

| 服务类型 | 服务名称 | 默认端口 | 说明 |
|---------|---------|---------|------|
| REAL | Math | 8000 | 数学计算服务 |
| REAL | Trade | 8002 | 交易执行服务 |
| FAKE | FakeSearch | 8006 | 假新闻搜索 |
| FAKE | FakePrices | 8008 | 假价格数据 |
| FAKE | FakeXSearch | 9009 | 假 X 搜索 |
| FAKE | FakeRedditSearch | 8010 | 假 Reddit 搜索 |

### 可自定义的端口键名

在 `CUSTOM_PORTS` 中可以使用以下键名：

```python
CUSTOM_PORTS = {
    'math': 8000,      # Math 服务端口
    'trade': 8002,     # Trade 服务端口
    'search': 8006,    # FakeSearch 端口
    'price': 8008,     # FakePrices 端口
    'x': 8009,         # FakeXSearch 端口
    'reddit': 8010,    # FakeRedditSearch 端口
}
```

---

## 🚀 运行命令

### 启动服务
```bash
python start_fake_mcp_services.py
```

### 查看状态
```bash
python start_fake_mcp_services.py status
```

### 停止服务
按 `Ctrl+C` 停止所有服务

---

## ❓ 常见问题

### Q1: 为什么默认不启动 Math 和 Trade？
**A:** 避免端口冲突。如果系统中已经运行了原始的 `start_mcp_services.py`，Math (8000) 和 Trade (8002) 端口会被占用，导致启动失败并自动停止所有服务。

### Q2: 我需要 Math 和 Trade 功能怎么办？
**A:** 
1. 先停止原有的 MCP 服务（如果在运行）
2. 将 `ENABLE_REAL_SERVICES` 改为 `True`
3. 运行 `python start_fake_mcp_services.py`

### Q3: 如何验证服务正在运行？
**A:** 
```bash
# 方式1：使用内置状态检查
python start_fake_mcp_services.py status

# 方式2：检查端口占用
lsof -i :8006 -i :8008 -i :8009 -i :8010
```

### Q4: 服务自动停止了怎么办？
**A:** 
1. 检查日志文件：`fake_service_log/*.log`
2. 常见原因：端口被占用、依赖包缺失
3. 确保 `ENABLE_REAL_SERVICES = False`（如果不需要 Math/Trade）

---

## 📚 相关文档

- [README.md](README.md) - 完整项目说明
- [QUICK_START.md](QUICK_START.md) - 快速入门
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - 使用示例
- [fake_data/README.md](fake_data/README.md) - 数据配置说明

---

## ✨ 优势

- ✅ **简单直观**：配置在代码开头，一目了然
- ✅ **无需参数**：直接运行即可，不用记住复杂的命令行参数
- ✅ **避免冲突**：默认不启动 Math/Trade，避免端口冲突
- ✅ **易于调试**：所有配置都在一个地方，便于快速修改

---

**Last Updated:** 2025-11-03


