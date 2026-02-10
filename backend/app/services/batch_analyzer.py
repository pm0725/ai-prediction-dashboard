"""
智链预测 - 批量分析服务
=======================
支持并发分析多个交易对，提高整体处理效率

功能:
    - 批量获取市场数据
    - 并发AI分析
    - 限流控制
    - 进度跟踪
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from app.services.data_aggregator import prepare_context_for_ai
from app.engines.deepseek_analyst import get_analyst, AnalysisResult
from app.services.cache_service import get_cached_analyzer

logger = logging.getLogger(__name__)


class AnalysisStatus(Enum):
    """分析状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class SymbolAnalysisResult:
    """单个交易对分析结果"""
    symbol: str
    timeframe: str
    status: AnalysisStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0
    from_cache: bool = False


@dataclass
class BatchAnalysisResult:
    """批量分析结果"""
    total: int
    success: int
    failed: int
    cached: int
    total_duration_ms: float
    results: List[SymbolAnalysisResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total": self.total,
                "success": self.success,
                "failed": self.failed,
                "cached": self.cached,
                "total_duration_ms": round(self.total_duration_ms, 2)
            },
            "results": [
                {
                    "symbol": r.symbol,
                    "timeframe": r.timeframe,
                    "status": r.status.value,
                    "result": r.result,
                    "error": r.error,
                    "duration_ms": round(r.duration_ms, 2),
                    "from_cache": r.from_cache
                }
                for r in self.results
            ]
        }


class BatchAnalyzer:
    """批量分析器"""
    
    def __init__(
        self,
        max_concurrency: int = 5,
        use_cache: bool = True,
        timeout_seconds: int = 60,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ):
        """
        Args:
            max_concurrency: 最大并发数
            use_cache: 是否使用缓存
            timeout_seconds: 单个分析超时时间
            progress_callback: 进度回调函数 (current, total, symbol)
        """
        self.max_concurrency = max_concurrency
        self.use_cache = use_cache
        self.timeout_seconds = timeout_seconds
        self.progress_callback = progress_callback
        
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def analyze_symbol(
        self,
        symbol: str,
        timeframe: str = "4h",
        model: Optional[str] = None,
        prompt_template: Optional[str] = None
    ) -> SymbolAnalysisResult:
        """分析单个交易对"""
        import time
        start_time = time.perf_counter()
        
        try:
            cache = get_cached_analyzer()
            
            # 检查缓存
            if self.use_cache:
                cached_result = cache.get_cached_analysis(symbol, timeframe)
                if cached_result:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    return SymbolAnalysisResult(
                        symbol=symbol,
                        timeframe=timeframe,
                        status=AnalysisStatus.CACHED,
                        result=cached_result,
                        duration_ms=duration_ms,
                        from_cache=True
                    )
            
            # 1. 准备市场上下文
            try:
                context = await prepare_context_for_ai(symbol, timeframe=timeframe)
            except Exception as e:
                logger.error(f"准备上下文失败 {symbol}: {e}")
                raise
            
            # 2. 调用AI分析 (使用统一的 DeepSeekAnalyst)
            try:
                # 引入指数避让重试逻辑
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        analyst = get_analyst()
                        
                        # 注入用户偏好 (关键补丁: 对齐 predict 端的逻辑)
                        context_dict = context.to_dict()
                        context_dict["user_preferences"] = {
                            "depth": 2, # Batch 默认 standard
                            "risk": "moderate",
                            "model": model,
                            "prompt_template": prompt_template
                        }

                        result = await asyncio.wait_for(
                            analyst.analyze_market(symbol, context_dict),
                            timeout=self.timeout_seconds
                        )
                        break # 成功则退出重试循环
                    except (Exception) as e:
                        if "429" in str(e) or "rate limit" in str(e).lower():
                            wait_time = (attempt + 1) * 2
                            logger.warning(f"触发速率限制 {symbol}, 等待 {wait_time}s 后重试 ({attempt+1}/{max_retries})")
                            await asyncio.sleep(wait_time)
                            if attempt == max_retries - 1: raise
                        else:
                            raise # 其他非限流错误直接抛出
                
                # 3. 注入透传数据
                result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict() # CRIT-4 修复: Pydantic v1/v2 兼容
                context_dict = context.to_dict()
                if "trend_context" in context_dict:
                    result_dict["trend_context"] = context_dict["trend_context"]
                if "order_book" in context_dict:
                    result_dict["order_book_context"] = context_dict["order_book"]
                
                result_dict["from_cache"] = False
                
                # 缓存项
                cache.cache_analysis(symbol, timeframe, result_dict)
                
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                return SymbolAnalysisResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    status=AnalysisStatus.SUCCESS,
                    result=result_dict,
                    duration_ms=duration_ms,
                    from_cache=False
                )
                
            except ValueError as e:
                # API未配置，返回基于技术指标的模拟结果
                logger.warning(f"DeepSeek API未配置，{symbol}使用模拟分析")
                
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                return SymbolAnalysisResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    status=AnalysisStatus.SUCCESS,
                    result={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "prediction": "neutral",
                        "prediction_cn": "震荡",
                        "confidence": 50,
                        "summary": f"[模拟] {symbol}技术面中性",
                        "from_cache": False,
                        "is_mock": True
                    },
                    duration_ms=duration_ms,
                    from_cache=False
                )
                
        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"AI分析超时 {symbol}, 尝试降级为技术分析")
            
            # 降级策略：如果有上下文，基于技术指标生成结果
            if 'context' in locals() and context:
                try:
                    # 简单的技术分析规则
                    indicators = context.indicators
                    trend = indicators.trend_status  # "up", "down", "sideways"
                    rsi = indicators.rsi_14
                    
                    direction = "Neutral"
                    if trend == "up":
                        direction = "Bullish"
                    elif trend == "down":
                        direction = "Bearish"
                    
                    # 修正方向 (RSI超买超卖)
                    if rsi > 75 and direction == "Bullish":
                        direction = "Neutral" # 潜在回调
                    elif rsi < 25 and direction == "Bearish":
                        direction = "Neutral" # 潜在反弹
                        
                    fallback_result = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "prediction": direction,
                        "prediction_cn": "看涨" if direction == "Bullish" else ("看跌" if direction == "Bearish" else "震荡"),
                        "confidence": 60, # 降级结果置信度较低
                        "reasoning": [f"AI响应超时，基于技术指标分析: 趋势{trend}, RSI {rsi:.1f}"],  # MED-3 修复: 必须是列表
                        "key_levels": {
                            "supports": [context.current_price * 0.95],
                            "resistances": [context.current_price * 1.05],
                            "current_price": context.current_price
                        },
                        "risk_level": "medium",
                        "summary": f"当前呈现{trend}趋势，技术指标显示{direction}信号 (自动降级模式)",
                        "entry_zone": None,
                        "stop_loss": None,
                        "take_profit": None,
                        "from_cache": False,
                        "is_fallback": True
                    }
                    
                    return SymbolAnalysisResult(
                        symbol=symbol,
                        timeframe=timeframe,
                        status=AnalysisStatus.SUCCESS,
                        result=fallback_result,
                        duration_ms=duration_ms,
                        from_cache=False
                    )
                except Exception as fallback_err:
                     logger.error(f"降级分析失败: {fallback_err}")
            
            return SymbolAnalysisResult(
                symbol=symbol,
                timeframe=timeframe,
                status=AnalysisStatus.FAILED,
                error=f"分析超时 (>{self.timeout_seconds}s)",
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"分析{symbol}失败: {e}")
            return SymbolAnalysisResult(
                symbol=symbol,
                timeframe=timeframe,
                status=AnalysisStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def _analyze_with_semaphore(
        self,
        symbol: str,
        timeframe: str,
        index: int,
        total: int,
        model: Optional[str] = None,
        prompt_template: Optional[str] = None
    ) -> SymbolAnalysisResult:
        """带信号量控制的分析"""
        async with self._semaphore:
            logger.info(f"开始分析 [{index+1}/{total}]: {symbol}")
            
            if self.progress_callback:
                self.progress_callback(index + 1, total, symbol)
            
            return await self.analyze_symbol(symbol, timeframe, model=model, prompt_template=prompt_template)
    
    async def batch_analyze(
        self,
        symbols: List[str],
        timeframe: str = "4h",
        model: Optional[str] = None,
        prompt_template: Optional[str] = None
    ) -> BatchAnalysisResult:
        """
        批量分析多个交易对
        
        Args:
            symbols: 交易对列表
            timeframe: 分析周期
            
        Returns:
            BatchAnalysisResult: 批量分析结果
        """
        import time
        start_time = time.perf_counter()
        
        logger.info(f"开始批量分析 {len(symbols)} 个交易对")
        
        # 创建信号量控制并发
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        
        # 创建所有任务
        tasks = [
            self._analyze_with_semaphore(symbol, timeframe, i, len(symbols), model=model, prompt_template=prompt_template)
            for i, symbol in enumerate(symbols)
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        analysis_results = []
        success_count = 0
        failed_count = 0
        cached_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 未捕获的异常
                analysis_results.append(SymbolAnalysisResult(
                    symbol=symbols[i],
                    timeframe=timeframe,
                    status=AnalysisStatus.FAILED,
                    error=str(result)
                ))
                failed_count += 1
            else:
                analysis_results.append(result)
                if result.status == AnalysisStatus.SUCCESS:
                    success_count += 1
                elif result.status == AnalysisStatus.CACHED:
                    cached_count += 1
                else:
                    failed_count += 1
        
        total_duration = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"批量分析完成: 成功={success_count}, 失败={failed_count}, "
            f"缓存={cached_count}, 耗时={total_duration:.0f}ms"
        )
        
        return BatchAnalysisResult(
            total=len(symbols),
            success=success_count,
            failed=failed_count,
            cached=cached_count,
            total_duration_ms=total_duration,
            results=analysis_results
        )
    
    async def analyze_all_major_symbols(
        self,
        timeframe: str = "4h"
    ) -> BatchAnalysisResult:
        """分析所有主流交易对"""
        major_symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT"
        ]
        return await self.batch_analyze(major_symbols, timeframe)


# ============================================================
# 便捷函数
# ============================================================

async def batch_analyze(
    symbols: List[str],
    timeframe: str = "4h",
    max_concurrency: int = 5,
    use_cache: bool = True,
    model: Optional[str] = None,
    prompt_template: Optional[str] = None
) -> BatchAnalysisResult:
    """
    批量分析多个交易对（便捷函数）
    
    Args:
        symbols: 交易对列表
        timeframe: 分析周期
        max_concurrency: 最大并发数
        use_cache: 是否使用缓存
        
    Returns:
        BatchAnalysisResult: 批量分析结果
    """
    analyzer = BatchAnalyzer(
        max_concurrency=max_concurrency,
        use_cache=use_cache
    )
    return await analyzer.batch_analyze(symbols, timeframe, model=model, prompt_template=prompt_template)


async def analyze_all_symbols(timeframe: str = "4h") -> BatchAnalysisResult:
    """分析所有主流交易对"""
    analyzer = BatchAnalyzer()
    return await analyzer.analyze_all_major_symbols(timeframe)


# ============================================================
# 测试入口
# ============================================================

async def main():
    """测试批量分析"""
    print("\n" + "="*60)
    print("  智链预测 - 批量分析测试")
    print("="*60 + "\n")
    
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    def progress(current, total, symbol):
        print(f"  进度: [{current}/{total}] {symbol}")
    
    analyzer = BatchAnalyzer(
        max_concurrency=3,
        use_cache=True,
        progress_callback=progress
    )
    
    result = await analyzer.batch_analyze(symbols, "4h")
    
    print("\n" + "-"*40)
    print(f"  总计: {result.total}")
    print(f"  成功: {result.success}")
    print(f"  失败: {result.failed}")
    print(f"  缓存: {result.cached}")
    print(f"  耗时: {result.total_duration_ms:.0f}ms")
    print("-"*40)
    
    for r in result.results:
        status = "✅" if r.status == AnalysisStatus.SUCCESS else "📦" if r.status == AnalysisStatus.CACHED else "❌"
        print(f"  {status} {r.symbol}: {r.result.get('prediction_cn', '未知') if r.result else r.error}")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())
