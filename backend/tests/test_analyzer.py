"""
智链预测 - 技术分析器单元测试
==============================
测试TechnicalAnalyzer和MarketAnalyzer的核心功能
"""

import pytest
from unittest.mock import patch, MagicMock
import math

import sys
sys.path.insert(0, '/Users/car/ai预测/backend')

from app.services.analyzer import (
    TechnicalAnalyzer,
    TechnicalIndicators,
    MarketAnalyzer,
    MarketAnalysis,
    get_market_analyzer
)
from app.services.data_fetcher import Kline, Ticker, FundingRate


# ============================================================
# 测试数据
# ============================================================

def generate_test_klines(count: int = 50, base_price: float = 65000.0):
    """生成测试K线数据"""
    import random
    random.seed(42)  # 固定随机种子以确保可重复
    
    klines = []
    price = base_price
    now = 1704067200000  # 固定时间戳
    interval = 4 * 60 * 60 * 1000  # 4小时
    
    for i in range(count):
        change = random.uniform(-0.02, 0.02)
        open_price = price
        close_price = price * (1 + change)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        
        klines.append(Kline(
            timestamp=now + i * interval,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=random.uniform(1000, 5000)
        ))
        
        price = close_price
    
    return klines


# ============================================================
# TechnicalAnalyzer测试
# ============================================================

class TestTechnicalAnalyzer:
    """测试技术分析计算器"""
    
    @pytest.fixture
    def analyzer(self):
        return TechnicalAnalyzer()
    
    @pytest.fixture
    def sample_prices(self):
        """简单的上涨价格序列"""
        return [100, 102, 104, 103, 105, 107, 106, 108, 110, 109, 
                111, 113, 112, 114, 116, 115, 117, 119, 118, 120]
    
    @pytest.fixture
    def sample_klines(self):
        """生成50根测试K线"""
        return generate_test_klines(50)
    
    # SMA测试
    def test_calculate_sma_basic(self, analyzer, sample_prices):
        """测试SMA基本计算"""
        sma = analyzer.calculate_sma(sample_prices, 5)
        
        # 最后5个价格: 117, 119, 118, 120 -> 平均
        expected = sum(sample_prices[-5:]) / 5
        assert abs(sma - expected) < 0.01
    
    def test_calculate_sma_insufficient_data(self, analyzer):
        """测试数据不足时的SMA计算"""
        prices = [100, 101, 102]
        sma = analyzer.calculate_sma(prices, 10)
        
        # 数据不足时返回最后一个价格
        assert sma == 102
    
    def test_calculate_sma_empty(self, analyzer):
        """测试空数据时的SMA计算"""
        sma = analyzer.calculate_sma([], 10)
        assert sma == 0
    
    # EMA测试
    def test_calculate_ema_basic(self, analyzer, sample_prices):
        """测试EMA基本计算"""
        ema = analyzer.calculate_ema(sample_prices, 5)
        
        # EMA应该更接近近期价格
        sma = analyzer.calculate_sma(sample_prices, 5)
        # 由于价格上涨，EMA应该略高于SMA
        # 这里只验证计算能正常返回
        assert ema > 0
    
    def test_calculate_ema_insufficient_data(self, analyzer):
        """测试数据不足时的EMA计算"""
        prices = [100, 101]
        ema = analyzer.calculate_ema(prices, 10)
        assert ema == 101
    
    # RSI测试
    def test_calculate_rsi_uptrend(self, analyzer):
        """测试上涨趋势中的RSI"""
        # 连续上涨的价格
        prices = list(range(100, 130))  # 100, 101, ... 129
        rsi = analyzer.calculate_rsi(prices, 14)
        
        # 上涨趋势中RSI应该较高
        assert rsi > 60
    
    def test_calculate_rsi_downtrend(self, analyzer):
        """测试下跌趋势中的RSI"""
        # 连续下跌的价格
        prices = list(range(130, 100, -1))  # 130, 129, ... 101
        rsi = analyzer.calculate_rsi(prices, 14)
        
        # 下跌趋势中RSI应该较低
        assert rsi < 40
    
    def test_calculate_rsi_neutral(self, analyzer):
        """测试震荡行情中的RSI"""
        # 震荡价格
        prices = [100, 101, 100, 101, 100, 101, 100, 101, 100, 101,
                  100, 101, 100, 101, 100, 101, 100, 101, 100, 101]
        rsi = analyzer.calculate_rsi(prices, 14)
        
        # 震荡行情RSI应该接近50
        assert 40 < rsi < 60
    
    def test_calculate_rsi_bounds(self, analyzer, sample_prices):
        """测试RSI边界值"""
        rsi = analyzer.calculate_rsi(sample_prices, 14)
        
        # RSI应该在0-100之间
        assert 0 <= rsi <= 100
    
    # MACD测试
    def test_calculate_macd(self, analyzer, sample_prices):
        """测试MACD计算"""
        macd_line, signal_line, histogram = analyzer.calculate_macd(sample_prices)
        
        # 基本验证
        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)
        assert isinstance(histogram, float)
        
        # 柱状图 = MACD线 - 信号线
        assert abs(histogram - (macd_line - signal_line)) < 0.0001
    
    def test_calculate_macd_insufficient_data(self, analyzer):
        """测试数据不足时的MACD"""
        prices = [100, 101, 102]
        macd_line, signal_line, histogram = analyzer.calculate_macd(prices)
        
        assert macd_line == 0
        assert signal_line == 0
        assert histogram == 0
    
    # 布林带测试
    def test_calculate_bollinger_bands(self, analyzer, sample_prices):
        """测试布林带计算"""
        upper, middle, lower = analyzer.calculate_bollinger_bands(sample_prices, 20, 2.0)
        
        # 上轨 > 中轨 > 下轨
        assert upper > middle > lower
        
        # 中轨应该等于SMA
        expected_middle = analyzer.calculate_sma(sample_prices, 20)
        assert abs(middle - expected_middle) < 0.01
    
    def test_calculate_bollinger_bands_width(self, analyzer):
        """测试布林带宽度"""
        # 低波动数据
        low_vol = [100] * 30
        upper1, middle1, lower1 = analyzer.calculate_bollinger_bands(low_vol, 20)
        
        # 高波动数据
        high_vol = []
        for i in range(30):
            high_vol.append(100 + (i % 2) * 20)  # 100, 120, 100, 120...
        upper2, middle2, lower2 = analyzer.calculate_bollinger_bands(high_vol, 20)
        
        # 高波动的布林带宽度应该更大
        width1 = upper1 - lower1
        width2 = upper2 - lower2
        assert width2 > width1
    
    # ATR测试
    def test_calculate_atr(self, analyzer, sample_klines):
        """测试ATR计算"""
        atr = analyzer.calculate_atr(sample_klines, 14)
        
        assert atr > 0
    
    def test_calculate_atr_insufficient_data(self, analyzer):
        """测试数据不足时的ATR"""
        klines = [Kline(1704067200000, 100, 105, 95, 102, 1000)]
        atr = analyzer.calculate_atr(klines, 14)
        
        assert atr == 0
    
    # 完整分析测试
    def test_analyze_complete(self, analyzer, sample_klines):
        """测试完整技术分析"""
        indicators = analyzer.analyze(sample_klines)
        
        assert isinstance(indicators, TechnicalIndicators)
        assert indicators.sma_20 > 0
        assert indicators.sma_50 > 0
        assert 0 <= indicators.rsi_14 <= 100
        assert indicators.trend_status in ["bullish", "bearish", "neutral"]
    
    def test_analyze_empty_data(self, analyzer):
        """测试空数据分析"""
        indicators = analyzer.analyze([])
        
        assert isinstance(indicators, TechnicalIndicators)
        # 应该返回默认值


# ============================================================
# MarketAnalyzer测试
# ============================================================

class TestMarketAnalyzer:
    """测试市场分析器"""
    
    @pytest.fixture
    def analyzer(self):
        return MarketAnalyzer()
    
    @pytest.fixture
    def sample_klines(self):
        return generate_test_klines(50)
    
    @pytest.fixture
    def sample_ticker(self):
        return Ticker(
            symbol="BTCUSDT",
            last_price=65500.0,
            bid_price=65499.5,
            ask_price=65500.5,
            volume_24h=50000.0,
            change_24h=2.35,
            high_24h=66000.0,
            low_24h=64000.0
        )
    
    @pytest.fixture
    def sample_funding(self):
        return FundingRate(
            symbol="BTCUSDT",
            funding_rate=0.0001,
            funding_time=1704067200000,
            mark_price=65500.0
        )
    
    def test_analyze_market_basic(self, analyzer, sample_klines, sample_ticker, sample_funding):
        """测试基本市场分析"""
        analysis = analyzer.analyze_market(
            symbol="BTCUSDT",
            klines=sample_klines,
            ticker=sample_ticker,
            funding=sample_funding
        )
        
        assert isinstance(analysis, MarketAnalysis)
        assert analysis.symbol == "BTCUSDT"
        assert analysis.current_price > 0
        assert analysis.indicators is not None
    
    def test_analyze_market_without_optional(self, analyzer, sample_klines):
        """测试无可选参数的市场分析"""
        analysis = analyzer.analyze_market(
            symbol="BTCUSDT",
            klines=sample_klines
        )
        
        assert analysis.symbol == "BTCUSDT"
        assert analysis.current_price > 0
    
    def test_analyze_sentiment(self, analyzer):
        """测试情绪分析"""
        # 看涨情绪
        bullish_indicators = TechnicalIndicators(
            rsi_14=65,
            macd_histogram=0.001,
            trend_status="bullish"
        )
        sentiment = analyzer._analyze_sentiment(bullish_indicators, 0.0001)
        assert sentiment in ["偏多", "极度乐观"]
        
        # 看跌情绪
        bearish_indicators = TechnicalIndicators(
            rsi_14=35,
            macd_histogram=-0.001,
            trend_status="bearish"
        )
        sentiment = analyzer._analyze_sentiment(bearish_indicators, -0.0001)
        assert sentiment in ["偏空", "极度悲观"]
    
    def test_format_context_for_ai(self, analyzer, sample_klines, sample_ticker, sample_funding):
        """测试AI上下文格式化"""
        analysis = analyzer.analyze_market(
            symbol="BTCUSDT",
            klines=sample_klines,
            ticker=sample_ticker,
            funding=sample_funding
        )
        
        context = analyzer.format_context_for_ai(analysis)
        
        assert isinstance(context, str)
        assert "BTCUSDT" in context
        assert "RSI" in context
        assert "MACD" in context
        assert "价格信息" in context
        assert "技术指标" in context
    
    def test_to_dict(self, analyzer, sample_klines):
        """测试分析结果序列化"""
        analysis = analyzer.analyze_market(
            symbol="BTCUSDT",
            klines=sample_klines
        )
        
        data = analysis.to_dict()
        
        assert isinstance(data, dict)
        assert data["symbol"] == "BTCUSDT"
        assert "indicators" in data
        assert "key_levels" in data


class TestGetMarketAnalyzer:
    """测试工厂函数"""
    
    def test_get_analyzer_singleton(self):
        """测试分析器单例模式"""
        import app.services.analyzer as module
        module._analyzer_instance = None
        
        analyzer1 = get_market_analyzer()
        analyzer2 = get_market_analyzer()
        
        assert analyzer1 is analyzer2


# ============================================================
# 运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
