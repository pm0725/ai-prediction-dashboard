"""
智链预测 - 分析API端点单元测试
================================
测试FastAPI分析路由的核心功能
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
import json
import sys
import os

# 确保能导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.analysis import router
from app.services.data_fetcher import Kline, Ticker, FundingRate
from app.services.analyzer import MarketAnalysis
from app.services.data_aggregator import MarketContext
from app.models.indicators import TechnicalIndicators
from app.engines import AnalysisResult

# ============================================================
# 测试设置
# ============================================================

app = FastAPI()
app.include_router(router)
client = TestClient(app)

# ============================================================
# 测试数据
# ============================================================

MOCK_MARKET_CONTEXT = MarketContext(
    symbol="BTCUSDT",
    current_price=65000.0,
    kline_summary="BTC处于上涨趋势",
    klines=[], # Mock klines
    indicators=TechnicalIndicators(
        sma_20=64500.0,
        sma_50=63000.0,
        ema_12=64800.0,
        ema_26=64000.0,
        rsi_14=55.0,
        macd_line=100.0,
        macd_signal=50.0,
        macd_histogram=50.0,
        bb_upper=66000.0,
        bb_middle=65000.0,
        bb_lower=64000.0,
        bb_width=0.03,
        atr_14=500.0,
        trend_status="bullish",
        ma_cross_status="golden_cross"
    ),
    funding_rate=0.0001,
    open_interest=50000.0,
    news_headlines=["News 1", "News 2"],
    market_sentiment="偏多",
    # Optional fields
    order_book={"bids": [], "asks": []},
    trend_kline_summary="大级别上涨",
    trend_klines=[], # Mock trend klines
    trend_indicators=TechnicalIndicators(
        sma_20=60000.0, sma_50=58000.0, ema_12=0, ema_26=0, rsi_14=60, macd_line=0, macd_signal=0, macd_histogram=0, bb_upper=0, bb_middle=0, bb_lower=0, bb_width=0, atr_14=0, trend_status="bullish", ma_cross_status="none"
    ),
    pivot_points={"R1": 66000, "S1": 64000}
)

MOCK_PREDICTION_RESULT = AnalysisResult(
    symbol="BTCUSDT",
    timeframe="4h",
    prediction="看涨",
    confidence=75,
    reasoning=["RSI超卖反弹", "MACD金叉"],
    key_levels={"strong_resistance": 68000, "strong_support": 62000},
    suggested_action="逢低做多",
    risk_level="中",
    risk_warning=["注意波动"],
    summary="看涨趋势",
    analysis_time=datetime.now().isoformat()
)

# ============================================================
# 健康检查测试
# ============================================================

class TestHealthCheck:
    """测试健康检查端点"""
    
    def test_health_check_success(self):
        """测试健康检查成功"""
        response = client.get("/api/analysis/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

# ============================================================
# 交易对列表测试
# ============================================================

class TestSymbols:
    """测试交易对列表端点"""
    
    def test_get_symbols(self):
        """测试获取交易对列表"""
        response = client.get("/api/analysis/symbols")
        
        assert response.status_code == 200
        data = response.json()
        assert "symbols" in data
        assert len(data["symbols"]) > 0
        
        # 验证符号结构
        symbol = data["symbols"][0]
        assert "symbol" in symbol
        assert "name" in symbol
        assert "base" in symbol

# ============================================================
# 市场上下文测试
# ============================================================

class TestMarketContext:
    """测试市场上下文端点"""
    
    def test_get_context_success(self):
        """测试成功获取市场上下文"""
        # 注意：这里需要根据 analysis.py 中的实现来 mock
        # analysis.py 中使用的是 prepare_context_for_ai 函数
        with patch('app.api.routes.analysis.prepare_context_for_ai', new_callable=AsyncMock) as mock_prepare:
            
            mock_prepare.return_value = MOCK_MARKET_CONTEXT
            
            response = client.get("/api/analysis/context/BTCUSDT")
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTCUSDT"
            assert "current_price" in data
            assert "indicators" in data
            assert data["indicators"]["rsi_14"] == 55.0

# ============================================================
# 预测分析测试
# ============================================================

class TestPredict:
    """测试预测分析端点"""
    
    def test_predict_success(self):
        """测试成功的预测分析"""
        with patch('app.api.routes.analysis.prepare_context_for_ai', new_callable=AsyncMock) as mock_prepare, \
             patch('app.api.routes.analysis.get_analyst') as mock_get_analyst, \
             patch('app.api.routes.analysis.get_cached_analyzer') as mock_get_cache:
            
            # Mock context
            mock_prepare.return_value = MOCK_MARKET_CONTEXT
            
            # Mock Analyst
            mock_analyst = AsyncMock()
            mock_analyst.analyze_market.return_value = MOCK_PREDICTION_RESULT
            mock_get_analyst.return_value = mock_analyst
            
            # Mock Cache
            mock_cache = MagicMock()
            mock_cache.get_cached_analysis.return_value = None # Cache miss
            mock_get_cache.return_value = mock_cache
            
            response = client.post(
                "/api/analysis/predict",
                json={
                    "symbol": "BTCUSDT", 
                    "timeframe": "4h",
                    "analysis_depth": 2,
                    "risk_preference": "moderate"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTCUSDT"
            assert data["prediction"] == "看涨"
            assert data["confidence"] == 75

    def test_predict_from_cache(self):
        """测试从缓存获取预测结果"""
        with patch('app.api.routes.analysis.get_cached_analyzer') as mock_get_cache:
            
            mock_cache = MagicMock()
            mock_cache.get_cached_analysis.return_value = MOCK_PREDICTION_RESULT.model_dump()
            mock_get_cache.return_value = mock_cache
            
            response = client.post(
                "/api/analysis/predict",
                json={"symbol": "BTCUSDT", "timeframe": "4h"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTCUSDT"
            # 注意：cached_result 不一定包含 from_cache 字段，它是被添加进去的，或者 model_dump 不含它
            # analysis.py L116: return AnalysisResult(**cached_result)
            # 所以返回的 json 应该和 MOCK_PREDICTION_RESULT 一致

# ============================================================
# 策略生成测试
# ============================================================

class TestStrategyGenerate:
    """测试策略生成端点"""
    
    def test_generate_strategy_long(self):
        """测试生成做多策略"""
        request = {
            "symbol": "BTCUSDT",
            "prediction": "看涨",
            "confidence": 75,
            "entry_zone": {"low": 64500, "high": 65200},
            "stop_loss": 63000,
            "take_profit": [66500, 68000, 70000],
            "risk_level": "中"
        }
        
        response = client.post("/api/analysis/strategy/generate", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["direction"] == "多"
        assert "position_sizing" in data
        assert len(data["take_profit"]) == 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
