"""
智链预测 - 分析API路由
=======================
提供AI预测分析的REST API端点

Author: 智链预测团队
Version: 1.0.0
"""

from datetime import datetime
from typing import Optional, Union, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger

from app.engines import AnalysisResult, get_analyst
from app.services import (
    prepare_context_for_ai, 
    format_context_as_text, 
    batch_analyze,
    get_cached_analyzer
)
import asyncio
import json


# 创建路由器
router = APIRouter(prefix="/api/analysis", tags=["分析服务"])


# ============================================================
# 请求/响应模型
# ============================================================

class AnalysisRequest(BaseModel):
    """分析请求模型"""
    symbol: str = Field(..., description="交易对符号", example="ETHUSDT")
    timeframe: str = Field(default="4h", description="分析周期", example="4h")
    analysis_depth: Any = Field(default=2, description="分析深度 (1-3 或 quick/standard/deep)")
    risk_preference: Any = Field(default="moderate", description="风险偏好 (数字或 conservative/moderate/aggressive)")
    # [新增] AI配置透传
    model: Optional[str] = Field(default=None, description="AI模型 (deepseek-chat/deepseek-reasoner)")
    prompt_template: Optional[str] = Field(default=None, description="自定义系统提示词模板")


class StrategyRequest(BaseModel):
    """策略生成请求"""
    symbol: str
    prediction: str
    confidence: int
    entry_zone: Optional[dict] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[list[float]] = None
    risk_level: str
    # [新增] 链上数据透传
    on_chain_context: Optional[dict] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str

class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    symbols: list[str] = Field(..., description="交易对列表")
    timeframe: str = Field(default="4h", description="周期")
    use_cache: bool = Field(default=True, description="是否使用缓存")
    model: Optional[str] = Field(default=None, description="AI模型")
    prompt_template: Optional[str] = Field(default=None, description="自定义提示词模板")


# 分析师实例 (统一使用 app.engines 中的 get_analyst)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查端点
    
    返回服务状态信息
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@router.post("/predict", response_model=AnalysisResult)
async def predict(
    request: AnalysisRequest,
    use_cache: bool = Query(default=True, description="是否使用缓存")
):
    """
    AI预测分析端点
    
    接收交易对符号，聚合市场数据，调用DeepSeek进行分析，
    返回结构化的预测结果。
    """
    symbol = request.symbol.upper()
    timeframe = request.timeframe
    
    logger.info(f"收到分析请求: {symbol} (use_cache={use_cache}) | Model: {request.model}")
    
    try:
        # 1. 检查缓存
        cache = get_cached_analyzer()
        if use_cache:
            cached_result = cache.get_cached_analysis(symbol, timeframe)
            if cached_result:
                logger.info(f"命中缓存: {symbol}")
                return AnalysisResult(**cached_result)
        
        # 2. 聚合市场数据
        context = await prepare_context_for_ai(symbol, timeframe=timeframe)
        
        # 3. 调用AI分析
        analyst = get_analyst()
        
        # 归一化参数
        depth_val = request.analysis_depth
        if isinstance(depth_val, str):
            depth_map = {"quick": 1, "standard": 2, "deep": 3}
            depth_val = depth_map.get(depth_val.lower(), 2)
        
        risk_val = request.risk_preference
        if isinstance(risk_val, (int, float)):
            if risk_val <= 30: risk_val = "conservative"
            elif risk_val <= 70: risk_val = "moderate"
            else: risk_val = "aggressive"

        # 注入用户偏好 (包含新增的 model 和 prompt_template)
        context_dict = context.to_dict()
        context_dict["user_preferences"] = {
            "depth": depth_val,
            "risk": risk_val,
            "model": request.model,
            "prompt_template": request.prompt_template
        }
        
        result = await analyst.analyze_market(symbol, context_dict)
        
        # 4. 注入透传数据
        # Pydantic v1/v2 compatibility
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
        raw_context_dict = context.to_dict()
        
        if "trend_context" in raw_context_dict:
            result_dict["trend_context"] = raw_context_dict["trend_context"]
        if "order_book" in raw_context_dict:
            result_dict["order_book_context"] = raw_context_dict["order_book"]
            
        # 注入链上数据
        on_chain_data = {
            "whale_activity": raw_context_dict.get("whale_activity"),
            "liquidity_gaps": raw_context_dict.get("liquidity_gaps"),
            "volatility_score": raw_context_dict.get("volatility_score")
        }
        # 只要有任意一项非空，就注入
        if any(v is not None for v in on_chain_data.values()):
            result_dict["on_chain_context"] = on_chain_data
        
        # 5. 存入缓存
        # 强制刷新时间戳，确保前端认为是最新的
        result_dict["analysis_time"] = datetime.now().isoformat()
        
        cache.cache_analysis(symbol, timeframe, result_dict)
        
        logger.info(f"分析完成: {symbol} -> {result.prediction} | Time: {result_dict['analysis_time']}")
        return AnalysisResult(**result_dict)
        
    except ValueError as e:
        logger.error(f"分析配置错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析服务暂时不可用: {str(e)}")


@router.get("/predict/{symbol}")
async def predict_get(
    symbol: str,
    timeframe: str = Query(default="4h", description="分析周期")
):
    """
    AI预测分析端点 (GET方式)
    
    便捷的GET请求方式获取分析结果
    """
    return await predict(AnalysisRequest(symbol=symbol, timeframe=timeframe))

@router.post("/predict/stream")
async def predict_stream(
    request: AnalysisRequest,
    use_cache: bool = Query(default=True)
):
    """
    AI预测流式输出端点
    """
    symbol = request.symbol.upper()
    timeframe = request.timeframe
    logger.info(f"开启流式分析: {symbol} (use_cache={use_cache})")
    
    try:
        # 1. 检查缓存 (即使是流式，如果已有缓存结果，也可以直接返回缓存块或直接结束)
        # 简单处理：流式暂不强制缓存，或者先输出缓存内容
        
        # 2. 聚合市场数据
        context = await prepare_context_for_ai(symbol, timeframe=timeframe)
        
        # 3. 流式响应
        async def event_generator():
            analyst = get_analyst()
            
            # 归一化参数
            depth_val = request.analysis_depth
            if isinstance(depth_val, str):
                depth_map = {"quick": 1, "standard": 2, "deep": 3}
                depth_val = depth_map.get(depth_val.lower(), 2)
            
            risk_val = request.risk_preference
            if isinstance(risk_val, (int, float)):
                if risk_val <= 30: risk_val = "conservative"
                elif risk_val <= 70: risk_val = "moderate"
                else: risk_val = "aggressive"

            # 注入用户偏好
            context_dict = context.to_dict()
            context_dict["user_preferences"] = {
                "depth": depth_val,
                "risk": risk_val,
                "model": request.model,
                "prompt_template": request.prompt_template
            }

            async for chunk in analyst.analyze_market_stream(symbol, context_dict):
                if chunk:
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"流式分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-scan")
async def batch_scan(request: BatchAnalysisRequest):
    """
    全场扫描端点
    """
    try:
        result = await batch_analyze(
            symbols=request.symbols,
            timeframe=request.timeframe,
            use_cache=request.use_cache,
            model=request.model,
            prompt_template=request.prompt_template
        )
        return result.to_dict()
    except Exception as e:
        logger.exception(f"批量分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache():
    """清理所有分析缓存"""
    try:
        cache = get_cached_analyzer()
        stats = cache.clear_all()
        return {"status": "success", "cleared": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/{symbol}")
async def get_context(symbol: str):
    """
    获取市场上下文数据
    
    返回用于AI分析的原始市场数据，便于调试和验证
    """
    try:
        context = await prepare_context_for_ai(symbol.upper(), timeframe="4h") # 上下文查看默认4h
        
        return {
            "symbol": context.symbol,
            "current_price": context.current_price,
            "klines": context.klines,  # 新增
            "kline_summary": context.kline_summary,
            "indicators": context.indicators.to_dict(), # 使用统一的 to_dict (包含 SMC/VPVR)
            "funding_rate": context.funding_rate,
            "open_interest": context.open_interest,
            "volatility_score": context.volatility_score,
            "whale_activity": context.whale_activity,
            "liquidity_gaps": context.liquidity_gaps,
            "news_headlines": context.news_headlines,
            "market_sentiment": context.market_sentiment,
            # 新增字段 (修复前端无变化问题)
            "order_book": context.order_book,
            "trend_context": {
                "summary": context.trend_kline_summary,
                "rsi": context.trend_indicators.rsi_14 if context.trend_indicators else None,
                "trend_status": context.trend_indicators.trend_status if context.trend_indicators else "unknown"
            } if context.trend_kline_summary else None
        }
        
    except Exception as e:
        logger.exception(f"获取上下文失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy/generate")
async def generate_strategy(request: StrategyRequest):
    """
    生成详细交易策略
    
    基于AI分析结果生成可执行的交易策略
    """
    logger.info(f"生成策略请求: {request.symbol}")
    
    # 计算仓位大小（基于风险等级）
    risk_multiplier = {
        "低": 1.0,
        "中": 0.75,
        "高": 0.5,
        "极高": 0.25
    }.get(request.risk_level, 0.5)
    
    base_position = 5.0  # 基础仓位5%
    recommended_position = base_position * risk_multiplier * (request.confidence / 100)
    
    # 计算杠杆建议
    if request.risk_level == "低":
        max_leverage = 10
    elif request.risk_level == "中":
        max_leverage = 5
    else:
        max_leverage = 3
    
    strategy = {
        "symbol": request.symbol,
        "generated_at": datetime.now().isoformat(),
        "direction": "多" if request.prediction == "看涨" else ("空" if request.prediction == "看跌" else "观望"),
        "position_sizing": {
            "percentage_of_capital": round(recommended_position, 2),
            "max_leverage": max_leverage,
            "risk_per_trade": "2%"
        },
        "entry": request.entry_zone or {"type": "等待回调入场"},
        "stop_loss": {
            "price": request.stop_loss,
            "type": "固定止损"
        },
        "take_profit": [
            {"level": i + 1, "price": tp, "close_percentage": [50, 30, 20][i] if i < 3 else 100}
            for i, tp in enumerate(request.take_profit or [])
        ],
        "trade_management": [
            "入场后立即设置止损单",
            "达到TP1后将止损移至成本价",
            "分批止盈，保留部分仓位追踪趋势"
        ],
        "warnings": [
            f"当前风险等级: {request.risk_level}",
            "请严格执行止损，单笔亏损不超过总资金2%",
            "如遇重大新闻事件，考虑提前减仓"
        ],
        "on_chain_context": request.on_chain_context  # [新增] 透传链上数据
    }
    
    return strategy


@router.get("/symbols")
async def get_supported_symbols():
    """
    获取支持的交易对列表
    """
    return {
        "symbols": [
            {"symbol": "BTCUSDT", "name": "比特币", "base": "BTC"},
            {"symbol": "ETHUSDT", "name": "以太坊", "base": "ETH"},
            {"symbol": "BNBUSDT", "name": "币安币", "base": "BNB"},
            {"symbol": "SOLUSDT", "name": "Solana", "base": "SOL"},
            {"symbol": "XRPUSDT", "name": "瑞波币", "base": "XRP"},
            {"symbol": "ADAUSDT", "name": "艾达币", "base": "ADA"},
            {"symbol": "DOGEUSDT", "name": "狗狗币", "base": "DOGE"},
            {"symbol": "AVAXUSDT", "name": "雪崩协议", "base": "AVAX"},
            {"symbol": "LINKUSDT", "name": "Chainlink", "base": "LINK"},
            {"symbol": "MATICUSDT", "name": "Polygon", "base": "MATIC"}
        ]
    }
