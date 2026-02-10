"""
智链预测 - 后端服务入口
========================
FastAPI应用主入口文件

Author: 智链预测团队
Version: 1.0.0
"""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

import asyncio
from app.api import analysis_router, market_router
from app.api.routes import websocket as websocket_router
from app.services.websocket_manager import manager
from app.services.data_aggregator import BinanceDataFetcher


# ============================================================
# 后台任务
# ============================================================

async def push_market_data():
    """后台任务：定期推送市场数据"""
    logger.info("启动行情推送任务...")
    fetcher = BinanceDataFetcher()
    # 关注的核心交易对
    symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"
    ]
    
    # 初始化波动率监控
    from app.services.volatility_monitor import VolatilityMonitor
    monitor = VolatilityMonitor(window_seconds=300) 
    
    # 记录上一次的成交量 (用于计算差值)
    last_volumes = {}

    try:
        # 启动长连接会话
        await fetcher.start_session()
        
        while True:
            try:
                # 获取最新行情 (复用 Session)
                tickers = await fetcher.get_tickers(symbols)
                
                # 1. 广播基础行情
                await manager.broadcast({
                    "type": "ticker_update",
                    "data": tickers,
                    "timestamp": time.time()  # B-MED-6 修复: 使用 time.time() 替代弃用的 get_event_loop().time()
                })

                # 2. 检查波动率和交易量预警
                alerts = []
                now = time.time()
                
                for t in tickers:
                    symbol = t['symbol']
                    price = float(t['price'])
                    current_vol = float(t.get('quote_volume', 0))
                    
                    # 计算 Volume Delta (近似当前周期的成交量)
                    # 这是一个近似值，因为 ticker 返回的是 24h 滚动成交量
                    # Vol_Delta = Vol_New - Vol_Old. 
                    # 如果 Vol_New < Vol_Old，说明旧的成交量滑出了24h窗口，此时无法准确计算，记为 0
                    if symbol in last_volumes:
                        vol_delta = current_vol - last_volumes[symbol]
                        if vol_delta < 0:
                            vol_delta = 0
                    else:
                        vol_delta = 0 # 第一次无法计算
                        
                    last_volumes[symbol] = current_vol
                    
                    # 注入数据 (Price & Volume Delta)
                    monitor.add_tick(symbol, price, vol_delta, now)
                    
                    # 检测
                    alert = monitor.check_volatility(symbol)
                    if alert:
                        alerts.append({
                            "symbol": alert.symbol,
                            "type": alert.type, # pump, dump, volume_spike
                            "severity": alert.severity, # low, medium, high
                            "change_percent": alert.change_percent,
                            "timeframe": alert.timeframe,
                            "message": alert.message,
                            "timestamp": alert.timestamp
                        })
                
                # 如果有预警，广播预警消息
                if alerts:
                    logger.warning(f"触发波动率预警: {len(alerts)} 个")
                    await manager.broadcast({
                        "type": "market_alerts",
                        "data": alerts,
                        "timestamp": now
                    })
                
            except Exception as e:
                logger.warning(f"行情推送周期异常: {e}")
                
            # 每2秒推送一次 (加快频率以捕捉瞬间波动)
            await asyncio.sleep(2)
    finally:
        # 确保关闭连接
        await fetcher.close_session()


# ============================================================
# 应用生命周期管理
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("="*50)
    logger.info("🚀 智链预测服务启动中...")
    logger.info("="*50)
    
    # 检查必要的环境变量
    if not os.getenv("DEEPSEEK_API_KEY"):
        logger.warning("⚠️  未设置 DEEPSEEK_API_KEY 环境变量")
        logger.warning("   请设置: export DEEPSEEK_API_KEY=your-api-key")
    else:
        logger.info("✅ DeepSeek API Key 已配置")
        
    # 启动后台推送任务
    push_task = asyncio.create_task(push_market_data())
    
    logger.info("✅ 服务启动完成")
    logger.info("-"*50)
    
    yield
    
    # 关闭时执行
    logger.info("-"*50)
    logger.info("👋 智链预测服务关闭中...")
    
    # 取消后台任务
    push_task.cancel()
    try:
        await push_task
    except asyncio.CancelledError:
        pass
        
    logger.info("="*50)


# ============================================================
# 创建FastAPI应用
# ============================================================

app = FastAPI(
    title="智链预测 API",
    description="""
## 面向专业用户的虚拟货币合约预测分析服务

### 核心功能
- **AI预测分析**: 基于DeepSeek大模型的智能市场分析
- **策略生成**: 根据分析结果生成可执行的交易策略
- **数据聚合**: 整合K线、技术指标、新闻等多维数据

### 技术特点
- 深度集成DeepSeek API
- 实时市场数据获取
- 结构化JSON响应
- 专业风险评估

> ⚠️ **免责声明**: 本服务仅供参考，不构成投资建议。加密货币交易存在高风险，请谨慎操作。
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ============================================================
# 中间件配置
# ============================================================

# CORS跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 注册路由
# ============================================================

app.include_router(analysis_router)
app.include_router(market_router, prefix="/api/market", tags=["市场数据"])
app.include_router(websocket_router.router)


# ============================================================
# 根路由
# ============================================================

@app.get("/", tags=["根路由"])
async def root():
    """
    API根路由，返回服务基本信息
    """
    return {
        "name": "智链预测 API",
        "version": "1.0.0",
        "description": "面向专业用户的虚拟货币合约预测分析服务",
        "docs": "/docs",
        "endpoints": {
            "health": "/api/analysis/health",
            "predict": "/api/analysis/predict",
            "symbols": "/api/analysis/symbols"
        }
    }


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
