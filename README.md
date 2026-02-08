# 智链预测 🔮

> AI驱动的虚拟货币合约预测分析平台

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Vue](https://img.shields.io/badge/Vue-3.4+-green.svg)](https://vuejs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal.svg)](https://fastapi.tiangolo.com)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-API-purple.svg)](https://deepseek.com)

---

## 📖 简介

智链预测是一款面向专业用户的中文虚拟货币合约预测分析软件，深度集成 DeepSeek API，利用大语言模型的逻辑推理能力提供：

- 🎯 **AI预测分析** - 基于实时盘口数据(Binance)的智能预测，支持**流式推理** (Streaming)
- 🚀 **全场扫描** - 并发扫描全市场热门币种，实时捕捉多空机会
- 📊 **策略生成** - 自动生成入场点位、止盈止损
- ⚠️ **风险预警** - 识别潜在市场风险事件
- 📈 **策略回测** - 验证AI策略历史表现

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- DeepSeek API Key

### 1. 克隆项目

```bash
cd /Users/car/ai预测
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境 (在项目根目录)
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
# 注意：如果在中国大陆地区，必须在 .env 中配置 HTTP_PROXY 才能连接 Binance 获取真实数据
```

### 3. 前端配置

```bash
cd frontend
npm install
```

### 4. 启动服务

lsof -i :8000 -t | xargs kill -9
**启动后端** (端口 8000)
```bash
# 方法一：使用显式路径 (最稳妥，推荐)
# 确保在 backend 目录下
cd backend
../.venv/bin/python main.py

# 方法二：先激活环境
# cd ..
# source .venv/bin/activate
# cd backend
# python main.py
```

**启动前端** (端口 5173，新终端)
```bash
cd frontend
npm run dev
```

### 5. 访问应用

| 服务 | 地址 |
|------|------|
| 前端应用 | http://localhost:5173 |
| 后端API | http://localhost:8000 |
| API文档 | http://localhost:8000/docs |

---

## 📁 项目结构

```
ai预测/
├── backend/                          # Python后端
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── analysis.py           # 分析API路由
│   │   │   └── prediction.py         # 预测API路由
│   │   ├── core/
│   │   │   └── config.py             # 配置管理
│   │   ├── engines/
│   │   │   └── deepseek_analyst.py   # DeepSeek AI引擎
│   │   └── services/
│   │       ├── deepseek_client.py    # DeepSeek客户端
│   │       ├── data_fetcher.py       # 数据获取器
│   │       ├── analyzer.py           # 技术分析器
│   │       └── data_aggregator.py    # 数据聚合模块
│   ├── main.py                       # FastAPI入口
│   ├── requirements.txt              # Python依赖
│   └── .env.example                  # 环境变量模板
│
├── frontend/                         # Vue3前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── AIPredictionCard.vue  # AI预测卡片
│   │   │   ├── PredictionPanel.vue   # 预测面板
│   │   │   ├── KLineChart.vue        # K线图组件
│   │   │   └── StrategyBoard.vue     # 策略展示板
│   │   ├── views/                    # 页面视图
│   │   ├── stores/
│   │   │   ├── market.ts             # 市场数据Store
│   │   │   └── usePredictionStore.ts # 预测状态Store
│   │   ├── services/api.ts           # API服务层
│   │   └── router/index.ts           # 路由配置
│   ├── package.json
│   └── vite.config.ts
│
└── scripts/
    └── start_dev.sh                  # 开发启动脚本
```

---

## 🔧 技术栈

### 后端
- **FastAPI** - 高性能异步Web框架
- **OpenAI SDK** - DeepSeek API调用
- **Pydantic** - 数据验证
- **HTTPX** - 异步HTTP客户端

### 前端
- **Vue 3** - 渐进式JavaScript框架
- **TypeScript** - 类型安全
- **Element Plus** - UI组件库
- **Pinia** - 状态管理
- **Vite** - 构建工具

### AI
- **DeepSeek Chat** - deepseek-chat模型
- **128K上下文** - 支持大量市场数据输入
- **JSON Mode** - 结构化输出

---

## 📡 API端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/analysis/health` | 健康检查 |
| POST | `/api/analysis/predict` | AI预测分析 (单次) |
| POST | `/api/analysis/predict/stream` | AI预测分析 (流式) |
| POST | `/api/analysis/batch-scan` | 批量市场扫描 |
| POST | `/api/analysis/cache/clear` | 强制缓存清理 |
| GET | `/api/analysis/context/{symbol}` | 获取市场上下文 |
| POST | `/api/analysis/strategy/generate` | 生成交易策略 |
| GET | `/api/analysis/symbols` | 交易对列表 |

---

## ⚙️ 环境变量

创建 `backend/.env` 文件：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 服务配置
DEBUG=true
LOG_LEVEL=INFO

# [可选] HTTP代理配置 (国内连接Binance必需)
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

---

## 🛡️ 免责声明

> ⚠️ **重要提示**
> 
> 本软件提供的所有分析结果和策略建议仅供参考，**不构成投资建议**。
> 
> 加密货币合约交易具有**极高风险性**，可能导致本金全部损失。请确保您完全理解相关风险后再进行交易。
> 
> 使用本软件进行交易的所有后果由用户自行承担。

---

## 📄 许可证

MIT License

---

## 🔗 相关链接

- [DeepSeek API文档](https://api-docs.deepseek.com/)
- [Vue 3文档](https://vuejs.org/)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Element Plus](https://element-plus.org/)
