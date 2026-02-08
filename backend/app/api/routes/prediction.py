"""
智链预测 - 预测API路由
======================
提供AI预测分析相关的API端点
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.engines import get_analyst, AnalysisResult
from app.services.data_fetcher import get_data_fetcher, DataFetcher
from app.services.analyzer import get_market_analyzer, MarketAnalyzer, MarketAnalysis
from app.services.cache_service import get_cached_analyzer, CachedAnalyzer
from app.services.batch_analyzer import BatchAnalyzer, batch_analyze, analyze_all_symbols
from app.services.data_aggregator import prepare_context_for_ai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prediction", tags=["预测分析"])


# ============================================================
# 请求/响应模型
# ============================================================

class PredictRequest(BaseModel):
    """预测请求"""
    symbol: str = Field(..., description="交易对符号", example="ETHUSDT")
    timeframe: str = Field(default="4h", description="分析周期", example="4h")


class BatchAnalyzeRequest(BaseModel):
    """批量分析请求"""
    symbols: List[str] = Field(..., description="交易对列表", example=["BTCUSDT", "ETHUSDT"])
    timeframe: str = Field(default="4h", description="分析周期", example="4h")
    max_concurrency: int = Field(default=5, description="最大并发数", ge=1, le=10)
    use_cache: bool = Field(default=True, description="是否使用缓存")


class StrategyRequest(BaseModel):
    """策略生成请求"""
    symbol: str
    prediction: str
    confidence: int
    entry_zone: Optional[dict] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[List[float]] = None
    risk_level: str = "中"


class StrategyResponse(BaseModel):
    """策略响应"""
    symbol: str
    generated_at: str
    direction: str
    position_sizing: dict
    entry: dict
    stop_loss: dict
    take_profit: List[dict]
    trade_management: List[str]
    warnings: List[str]


class SymbolInfo(BaseModel):
    """交易对信息"""
    symbol: str
    name: str
    base: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str
    deepseek_configured: bool


# ============================================================
# API端点
# ============================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康状态检查"""
    from app.core.config import settings
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        deepseek_configured=bool(settings.deepseek.api_key)
    )


@router.get("/symbols")
async def get_symbols():
    """获取支持的交易对列表"""
    symbols = [
        SymbolInfo(symbol="BTCUSDT", name="Bitcoin", base="BTC"),
        SymbolInfo(symbol="ETHUSDT", name="Ethereum", base="ETH"),
        SymbolInfo(symbol="BNBUSDT", name="BNB", base="BNB"),
        SymbolInfo(symbol="SOLUSDT", name="Solana", base="SOL"),
        SymbolInfo(symbol="XRPUSDT", name="Ripple", base="XRP"),
        SymbolInfo(symbol="ADAUSDT", name="Cardano", base="ADA"),
        SymbolInfo(symbol="DOGEUSDT", name="Dogecoin", base="DOGE"),
        SymbolInfo(symbol="AVAXUSDT", name="Avalanche", base="AVAX"),
        SymbolInfo(symbol="DOTUSDT", name="Polkadot", base="DOT"),
        SymbolInfo(symbol="MATICUSDT", name="Polygon", base="MATIC"),
    ]
    return {"symbols": [s.model_dump() for s in symbols]}


@router.get("/context/{symbol}")
async def get_market_context(
    symbol: str,
    timeframe: str = Query(default="4h", description="K线周期"),
    fetcher: DataFetcher = Depends(get_data_fetcher),
    analyzer: MarketAnalyzer = Depends(get_market_analyzer)
):
    """
    获取市场上下文数据
    
    - 获取K线、Ticker、资金费率
    - 计算技术指标
    - 返回结构化的市场分析
    """
    try:
        # 获取市场数据
        market_data = await fetcher.get_market_data(symbol, timeframe, kline_limit=50)
        
        # 执行分析
        analysis = analyzer.analyze_market(
            symbol=symbol,
            klines=market_data["klines"],
            ticker=market_data.get("ticker"),
            funding=market_data.get("funding")
        )
        
        return analysis.to_dict()
        
    except Exception as e:
        logger.error(f"获取市场上下文失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict")
async def predict(
    request: PredictRequest,
    use_cache: bool = Query(default=True, description="是否使用缓存"),
    fetcher: DataFetcher = Depends(get_data_fetcher),
    analyzer: MarketAnalyzer = Depends(get_market_analyzer)
):
    """
    执行AI预测分析
    
    1. 检查缓存是否有效
    2. 获取市场数据
    3. 计算技术指标
    4. 构建AI上下文
    5. 调用DeepSeek API
    6. 缓存并返回结果
    """
    try:
        logger.info(f"开始预测分析: {request.symbol} ({request.timeframe})")
        
        # 0. 检查缓存
        cache = get_cached_analyzer()
        if use_cache:
            cached_result = cache.get_cached_analysis(request.symbol, request.timeframe)
            if cached_result:
                logger.info(f"命中缓存: {request.symbol}/{request.timeframe}")
                cached_result["from_cache"] = True
                return cached_result
        
        # 1. 获取市场数据（尝试缓存）
        market_data = cache.get_cached_market_data(request.symbol, request.timeframe)
        if not market_data:
            market_data = await fetcher.get_market_data(
                request.symbol, 
                request.timeframe, 
                kline_limit=50
            )
            cache.cache_market_data(request.symbol, request.timeframe, market_data)
        
        # 2. 执行市场分析
        analysis = analyzer.analyze_market(
            symbol=request.symbol,
            klines=market_data["klines"],
            ticker=market_data.get("ticker"),
            funding=market_data.get("funding")
        )
        
        # 3. 构建AI上下文 (使用统一的 prepare_context_for_ai)
        context = await prepare_context_for_ai(request.symbol, request.timeframe)
        context_data = context.to_dict()  # 转换为字典供AI使用
        
        # 4. 调用DeepSeek API (使用统一的 DeepSeekAnalyst)
        try:
            analyst = get_analyst()
            result = await analyst.analyze_market(
                symbol=request.symbol,
                context_data=context_data
            )
            
            result_dict = result.model_dump()
            result_dict["from_cache"] = False
            
            # 5. 缓存结果
            cache.cache_analysis(request.symbol, request.timeframe, result_dict)
            
            return result_dict
            
        except ValueError as e:
            # API密钥未配置，返回模拟结果
            logger.warning(f"DeepSeek API未配置，返回模拟结果: {e}")
            mock_result = _generate_mock_prediction(request.symbol, request.timeframe, analysis)
            mock_result["from_cache"] = False
            cache.cache_analysis(request.symbol, request.timeframe, mock_result)
            return mock_result
        
    except Exception as e:
        logger.error(f"预测分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict/{symbol}")
async def predict_get(
    symbol: str,
    timeframe: str = Query(default="4h"),
    fetcher: DataFetcher = Depends(get_data_fetcher),
    analyzer: MarketAnalyzer = Depends(get_market_analyzer)
):
    """GET方式的预测分析（便于测试）"""
    request = PredictRequest(symbol=symbol, timeframe=timeframe)
    return await predict(request, fetcher, analyzer)


@router.post("/predict/stream")
async def predict_stream(
    request: PredictRequest,
    fetcher: DataFetcher = Depends(get_data_fetcher),
    analyzer: MarketAnalyzer = Depends(get_market_analyzer)
):
    """
    流式预测分析
    
    实时返回AI分析过程，用于前端展示思考过程
    """
    try:
        # 获取上下文数据 (使用统一的 prepare_context_for_ai)
        context = await prepare_context_for_ai(request.symbol, request.timeframe)
        context_data = context.to_dict()  # 转换为字典供AI使用
        
        # 流式响应 (使用统一的 DeepSeekAnalyst)
        async def generate():
            try:
                analyst = get_analyst()
                async for chunk in analyst.analyze_market_stream(
                    symbol=request.symbol,
                    context_data=context_data
                ):
                    yield f"data: {chunk}\n\n"
            except ValueError:
                yield "data: [系统] DeepSeek API未配置，请设置DEEPSEEK_API_KEY\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
        
    except Exception as e:
        logger.error(f"流式预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-analyze")
async def batch_analyze_endpoint(request: BatchAnalyzeRequest):
    """
    批量分析多个交易对
    
    并发执行多个交易对的分析，支持缓存和限流。
    适合首页概览或自选列表分析。
    """
    try:
        result = await batch_analyze(
            symbols=request.symbols,
            timeframe=request.timeframe,
            max_concurrency=request.max_concurrency,
            use_cache=request.use_cache
        )
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-all")
async def analyze_all_endpoint(timeframe: str = Query(default="4h")):
    """
    分析所有主流交易对
    """
    try:
        result = await analyze_all_symbols(timeframe)
        return result.to_dict()
    except Exception as e:
        logger.error(f"全局分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy/generate", response_model=StrategyResponse)
async def generate_strategy(request: StrategyRequest):
    """
    基于预测结果生成交易策略
    """
    try:
        # 根据风险等级确定仓位
        risk_position = {
            "低": {"percentage": 3, "leverage": 3},
            "中": {"percentage": 5, "leverage": 5},
            "高": {"percentage": 2, "leverage": 2},
            "极高": {"percentage": 1, "leverage": 1}
        }
        
        position = risk_position.get(request.risk_level, risk_position["中"])
        
        # 确定方向
        direction = "做多" if request.prediction == "看涨" else "做空" if request.prediction == "看跌" else "观望"
        
        # 构建入场策略
        entry = {
            "type": "限价单",
            "zone": request.entry_zone or {"low": 0, "high": 0},
            "condition": f"等待价格回调至入场区间内"
        }
        
        # 止损策略
        stop_loss = {
            "price": request.stop_loss or 0,
            "type": "固定止损",
            "note": "严格执行，不参与抄底/摸顶"
        }
        
        # 止盈策略
        take_profits = []
        if request.take_profit:
            for i, tp in enumerate(request.take_profit):
                take_profits.append({
                    "level": i + 1,
                    "price": tp,
                    "close_percentage": 30 if i == 0 else 50 if i == 1 else 100
                })
        
        # 交易管理建议
        management = [
            "入场后设置止损单，不可心存侥幸",
            "达到第一止盈位后，将止损移至成本价",
            "市场剧烈波动时，减小仓位或暂停交易",
            "每日最大亏损不超过总资金的5%"
        ]
        
        # 风险警告
        warnings = [
            "以上建议基于AI分析，不构成投资建议",
            "加密货币合约交易风险极高，可能损失全部本金",
            "请根据自身风险承受能力谨慎决策"
        ]
        
        return StrategyResponse(
            symbol=request.symbol,
            generated_at=datetime.now().isoformat(),
            direction=direction,
            position_sizing={
                "percentage_of_capital": position["percentage"],
                "max_leverage": position["leverage"],
                "risk_per_trade": "2%"
            },
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profits,
            trade_management=management,
            warnings=warnings
        )
        
    except Exception as e:
        logger.error(f"策略生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 缓存管理端点
# ============================================================

@router.get("/cache/stats")
async def cache_stats():
    """获取缓存统计信息"""
    cache = get_cached_analyzer()
    return {
        "status": "ok",
        "stats": cache.get_stats()
    }


@router.post("/cache/clear")
async def cache_clear():
    """清空所有缓存"""
    cache = get_cached_analyzer()
    cleared = cache.clear_all()
    return {
        "status": "ok",
        "cleared": cleared,
        "message": "缓存已清空"
    }


@router.post("/cache/invalidate/{symbol}")
async def cache_invalidate(
    symbol: str,
    timeframe: str = Query(default="4h")
):
    """使指定交易对的缓存失效"""
    cache = get_cached_analyzer()
    cache.invalidate(symbol, timeframe)
    return {
        "status": "ok",
        "message": f"缓存已失效: {symbol}/{timeframe}"
    }


# ============================================================
# 辅助函数
# ============================================================

def _generate_mock_prediction(
    symbol: str, 
    timeframe: str, 
    analysis: MarketAnalysis
) -> dict:
    """生成模拟预测结果（API未配置时使用）"""
    indicators = analysis.indicators
    
    # 基于技术指标简单判断
    score = 0
    if indicators.rsi_14 > 50:
        score += 1
    if indicators.macd_histogram > 0:
        score += 1
    if indicators.trend_status == "bullish":
        score += 2
    elif indicators.trend_status == "bearish":
        score -= 2
    
    if score >= 2:
        prediction = "看涨"
        confidence = min(65 + score * 5, 80)
    elif score <= -2:
        prediction = "看跌"
        confidence = min(65 + abs(score) * 5, 80)
    else:
        prediction = "震荡"
        confidence = 55
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "prediction": prediction,
        "confidence": confidence,
        "reasoning": [
            f"RSI({indicators.rsi_14:.1f})处于{'超买' if indicators.rsi_14 > 70 else '超卖' if indicators.rsi_14 < 30 else '中性'}区间",
            f"MACD柱状图{'为正' if indicators.macd_histogram > 0 else '为负'}，{'多头' if indicators.macd_histogram > 0 else '空头'}动能{'加强' if abs(indicators.macd_histogram) > 0 else '减弱'}",
            f"均线状态: {indicators.ma_cross_status}",
            f"当前趋势: {indicators.trend_status}",
            "[注意] 此为模拟结果，请配置DEEPSEEK_API_KEY获取真实AI分析"
        ],
        "key_levels": analysis.key_levels,
        "suggested_action": f"建议{'逢低做多' if prediction == '看涨' else '逢高做空' if prediction == '看跌' else '区间操作'}",
        "entry_zone": {
            "low": analysis.key_levels.get("weak_support", 0),
            "high": analysis.current_price
        } if prediction == "看涨" else {
            "low": analysis.current_price,
            "high": analysis.key_levels.get("weak_resistance", 0)
        },
        # 止损价：基于当前价格的合理幅度（3%），而非可能很远的关键位
        "stop_loss": (
            analysis.current_price * 0.97  # 看涨：止损在入场价下方 3%
            if prediction == "看涨" 
            else analysis.current_price * 1.03  # 看跌：止损在入场价上方 3%
        ),
        # 止盈价：使用合理的目标位
        "take_profit": [
            analysis.current_price * 1.02,  # TP1: +2%
            analysis.current_price * 1.05,  # TP2: +5%
            analysis.current_price * 1.08   # TP3: +8%
        ] if prediction == "看涨" else [
            analysis.current_price * 0.98,  # TP1: -2%
            analysis.current_price * 0.95,  # TP2: -5%
            analysis.current_price * 0.92   # TP3: -8%
        ],
        "risk_level": "中",
        "risk_warning": [
            "此为模拟预测，仅供参考",
            "请配置DeepSeek API获取专业分析"
        ],
        "summary": f"{symbol}当前处于{prediction}趋势，建议关注关键价位变化。(模拟结果)",
        "analysis_time": datetime.now().isoformat()
    }
