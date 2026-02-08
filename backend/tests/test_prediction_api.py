"""
智链预测 - 预测API端点单元测试
================================
测试FastAPI预测路由的核心功能
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
import json

import sys
sys.path.insert(0, '/Users/car/ai预测/backend')

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.prediction import router
from app.services.data_fetcher import Kline, Ticker, FundingRate
from app.services.analyzer import TechnicalIndicators, MarketAnalysis


# ============================================================
# 测试设置
# ============================================================

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ============================================================
# 测试数据
# ============================================================

MOCK_MARKET_CONTEXT = MarketAnalysis(
    symbol="BTCUSDT",
    current_price=65000.0,
    indicators=TechnicalIndicators(
        sma_20=64500.0,
        sma_50=63000.0,
        rsi_14=55.0,
        macd_histogram=0.001,
        trend_status="bullish"
    ),
    price_change_24h=2.35,
    volume_24h=50000.0,
    funding_rate=0.0001,
    market_sentiment="偏多",
    key_levels={
        "strong_resistance": 68000,
        "weak_resistance": 66500,
        "current_price": 65000,
        "weak_support": 63500,
        "strong_support": 62000
    },
    kline_summary="BTC处于上涨趋势"
)

MOCK_PREDICTION = {
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "prediction": "看涨",
    "confidence": 75,
    "reasoning": ["RSI超卖反弹", "MACD金叉"],
    "key_levels": {"strong_resistance": 68000, "strong_support": 62000},
    "suggested_action": "逢低做多",
    "risk_level": "中",
    "risk_warning": ["注意波动"],
    "summary": "看涨趋势",
    "analysis_time": datetime.now().isoformat()
}


# ============================================================
# 健康检查测试
# ============================================================

class TestHealthCheck:
    """测试健康检查端点"""
    
    def test_health_check_success(self):
        """测试健康检查成功"""
        with patch('app.api.routes.prediction.settings') as mock_settings:
            mock_settings.deepseek.api_key = "test-key"
            
            response = client.get("/prediction/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert data["version"] == "1.0.0"
    
    def test_health_check_no_api_key(self):
        """测试无API密钥时的健康检查"""
        with patch('app.api.routes.prediction.settings') as mock_settings:
            mock_settings.deepseek.api_key = ""
            
            response = client.get("/prediction/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["deepseek_configured"] is False


# ============================================================
# 交易对列表测试
# ============================================================

class TestSymbols:
    """测试交易对列表端点"""
    
    def test_get_symbols(self):
        """测试获取交易对列表"""
        response = client.get("/prediction/symbols")
        
        assert response.status_code == 200
        data = response.json()
        assert "symbols" in data
        assert len(data["symbols"]) > 0
        
        # 验证符号结构
        symbol = data["symbols"][0]
        assert "symbol" in symbol
        assert "name" in symbol
        assert "base" in symbol
    
    def test_symbols_contains_btc_eth(self):
        """测试交易对列表包含主要币种"""
        response = client.get("/prediction/symbols")
        
        data = response.json()
        symbols = [s["symbol"] for s in data["symbols"]]
        
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols


# ============================================================
# 市场上下文测试
# ============================================================

class TestMarketContext:
    """测试市场上下文端点"""
    
    def test_get_context_success(self):
        """测试成功获取市场上下文"""
        with patch('app.api.routes.prediction.get_data_fetcher') as mock_fetcher, \
             patch('app.api.routes.prediction.get_market_analyzer') as mock_analyzer:
            
            # 模拟数据获取
            mock_fetcher_instance = MagicMock()
            mock_fetcher_instance.get_market_data = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "timeframe": "4h",
                "klines": [Kline(1704067200000, 65000, 65500, 64800, 65200, 1000)],
                "ticker": Ticker("BTCUSDT", 65500, 65499, 65501, 50000, 2.35, 66000, 64000),
                "funding": FundingRate("BTCUSDT", 0.0001, 1704067200000, 65500)
            })
            mock_fetcher.return_value = mock_fetcher_instance
            
            # 模拟分析器
            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.analyze_market.return_value = MOCK_MARKET_CONTEXT
            mock_analyzer.return_value = mock_analyzer_instance
            
            response = client.get("/prediction/context/BTCUSDT")
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTCUSDT"
            assert "current_price" in data
            assert "indicators" in data


# ============================================================
# 预测分析测试
# ============================================================

class TestPredict:
    """测试预测分析端点"""
    
    def test_predict_success(self):
        """测试成功的预测分析"""
        with patch('app.api.routes.prediction.get_data_fetcher') as mock_fetcher, \
             patch('app.api.routes.prediction.get_market_analyzer') as mock_analyzer, \
             patch('app.api.routes.prediction.get_deepseek_client') as mock_client:
            
            # 设置模拟
            mock_fetcher_instance = MagicMock()
            mock_fetcher_instance.get_market_data = AsyncMock(return_value={
                "symbol": "BTCUSDT",
                "timeframe": "4h",
                "klines": [Kline(1704067200000, 65000, 65500, 64800, 65200, 1000)],
                "ticker": None,
                "funding": None
            })
            mock_fetcher.return_value = mock_fetcher_instance
            
            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.analyze_market.return_value = MOCK_MARKET_CONTEXT
            mock_analyzer_instance.format_context_for_ai.return_value = "Mock context"
            mock_analyzer.return_value = mock_analyzer_instance
            
            # 模拟DeepSeek客户端抛出ValueError（API未配置）
            mock_client.side_effect = ValueError("API key未配置")
            
            response = client.post(
                "/prediction/predict",
                json={"symbol": "BTCUSDT", "timeframe": "4h"}
            )
            
            # 应该返回模拟预测结果
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTCUSDT"
            assert "prediction" in data
            assert "confidence" in data
    
    def test_predict_get_method(self):
        """测试GET方式的预测分析"""
        with patch('app.api.routes.prediction.get_data_fetcher') as mock_fetcher, \
             patch('app.api.routes.prediction.get_market_analyzer') as mock_analyzer:
            
            mock_fetcher_instance = MagicMock()
            mock_fetcher_instance.get_market_data = AsyncMock(return_value={
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "klines": [Kline(1704067200000, 2600, 2650, 2580, 2620, 500)],
                "ticker": None,
                "funding": None
            })
            mock_fetcher.return_value = mock_fetcher_instance
            
            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.analyze_market.return_value = MarketAnalysis(
                symbol="ETHUSDT",
                current_price=2620.0,
                indicators=TechnicalIndicators()
            )
            mock_analyzer_instance.format_context_for_ai.return_value = "Mock context"
            mock_analyzer.return_value = mock_analyzer_instance
            
            response = client.get("/prediction/predict/ETHUSDT?timeframe=1h")
            
            assert response.status_code == 200
    
    def test_predict_invalid_request(self):
        """测试无效请求"""
        response = client.post(
            "/prediction/predict",
            json={}  # 缺少必需字段
        )
        
        assert response.status_code == 422  # Validation Error


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
        
        response = client.post("/prediction/strategy/generate", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["direction"] == "做多"
        assert "position_sizing" in data
        assert "entry" in data
        assert "stop_loss" in data
        assert "take_profit" in data
        assert len(data["take_profit"]) == 3
    
    def test_generate_strategy_short(self):
        """测试生成做空策略"""
        request = {
            "symbol": "ETHUSDT",
            "prediction": "看跌",
            "confidence": 65,
            "risk_level": "高"
        }
        
        response = client.post("/prediction/strategy/generate", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["direction"] == "做空"
        # 高风险应该使用较小仓位
        assert data["position_sizing"]["percentage_of_capital"] <= 3
    
    def test_generate_strategy_neutral(self):
        """测试震荡行情策略"""
        request = {
            "symbol": "BNBUSDT",
            "prediction": "震荡",
            "confidence": 50,
            "risk_level": "低"
        }
        
        response = client.post("/prediction/strategy/generate", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["direction"] == "观望"
    
    def test_strategy_has_warnings(self):
        """测试策略包含风险警告"""
        request = {
            "symbol": "BTCUSDT",
            "prediction": "看涨",
            "confidence": 75,
            "risk_level": "中"
        }
        
        response = client.post("/prediction/strategy/generate", json=request)
        
        data = response.json()
        assert "warnings" in data
        assert len(data["warnings"]) > 0
    
    def test_strategy_has_management_rules(self):
        """测试策略包含交易管理规则"""
        request = {
            "symbol": "BTCUSDT",
            "prediction": "看涨",
            "confidence": 75,
            "risk_level": "中"
        }
        
        response = client.post("/prediction/strategy/generate", json=request)
        
        data = response.json()
        assert "trade_management" in data
        assert len(data["trade_management"]) > 0


# ============================================================
# 运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
