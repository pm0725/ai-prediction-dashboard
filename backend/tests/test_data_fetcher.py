"""
智链预测 - 数据获取器单元测试
==============================
测试DataFetcher的核心功能
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
import asyncio

import sys
sys.path.insert(0, '/Users/car/ai预测/backend')

from app.services.data_fetcher import (
    DataFetcher,
    BinanceExchange,
    Kline,
    Ticker,
    FundingRate,
    OpenInterest,
    Timeframe,
    get_data_fetcher
)


# ============================================================
# 测试数据
# ============================================================

MOCK_KLINE_DATA = [
    [
        1704067200000,  # timestamp
        "65000.00",     # open
        "65500.00",     # high
        "64800.00",     # low
        "65200.00",     # close
        "1000.50",      # volume
        1704070800000,  # close_time
        "65200000.00",  # quote_volume
        1000,           # trades
        "500.00",       # taker_buy_base
        "32600000.00",  # taker_buy_quote
        "0"             # ignore
    ],
    [
        1704070800000,
        "65200.00",
        "65800.00",
        "65100.00",
        "65600.00",
        "1200.75",
        1704074400000,
        "78780000.00",
        1200,
        "600.00",
        "39480000.00",
        "0"
    ]
]

MOCK_TICKER_DATA = {
    "symbol": "BTCUSDT",
    "lastPrice": "65500.00",
    "bidPrice": "65499.50",
    "askPrice": "65500.50",
    "volume": "50000.00",
    "priceChangePercent": "2.35",
    "highPrice": "66000.00",
    "lowPrice": "64000.00"
}

MOCK_FUNDING_DATA = [
    {
        "symbol": "BTCUSDT",
        "fundingRate": "0.0001",
        "fundingTime": 1704067200000
    }
]


# ============================================================
# Kline测试
# ============================================================

class TestKline:
    """测试Kline数据类"""
    
    def test_create_kline(self):
        """测试创建K线对象"""
        kline = Kline(
            timestamp=1704067200000,
            open=65000.0,
            high=65500.0,
            low=64800.0,
            close=65200.0,
            volume=1000.5
        )
        
        assert kline.open == 65000.0
        assert kline.close == 65200.0
        assert kline.volume == 1000.5
    
    def test_is_bullish(self):
        """测试阳线判断"""
        bullish = Kline(
            timestamp=1704067200000,
            open=65000.0, high=65500.0, low=64800.0,
            close=65200.0, volume=1000.0
        )
        
        bearish = Kline(
            timestamp=1704067200000,
            open=65200.0, high=65500.0, low=64800.0,
            close=65000.0, volume=1000.0
        )
        
        assert bullish.is_bullish is True
        assert bearish.is_bullish is False
    
    def test_change_percent(self):
        """测试涨跌幅计算"""
        kline = Kline(
            timestamp=1704067200000,
            open=65000.0, high=65500.0, low=64800.0,
            close=65650.0, volume=1000.0
        )
        
        # (65650 - 65000) / 65000 * 100 = 1.0%
        assert abs(kline.change_percent - 1.0) < 0.01
    
    def test_body_size(self):
        """测试实体大小计算"""
        kline = Kline(
            timestamp=1704067200000,
            open=65000.0, high=65500.0, low=64800.0,
            close=65200.0, volume=1000.0
        )
        
        assert kline.body_size == 200.0


class TestTicker:
    """测试Ticker数据类"""
    
    def test_create_ticker(self):
        """测试创建Ticker对象"""
        ticker = Ticker(
            symbol="BTCUSDT",
            last_price=65500.0,
            bid_price=65499.5,
            ask_price=65500.5,
            volume_24h=50000.0,
            change_24h=2.35,
            high_24h=66000.0,
            low_24h=64000.0
        )
        
        assert ticker.symbol == "BTCUSDT"
        assert ticker.last_price == 65500.0
        assert ticker.change_24h == 2.35


# ============================================================
# BinanceExchange测试
# ============================================================

class TestBinanceExchange:
    """测试Binance交易所类"""
    
    @pytest.fixture
    def exchange(self):
        """创建交易所实例"""
        return BinanceExchange()
    
    @pytest.mark.asyncio
    async def test_get_klines_success(self, exchange):
        """测试成功获取K线数据"""
        with patch.object(exchange, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_KLINE_DATA
            
            klines = await exchange.get_klines("BTCUSDT", "4h", limit=2)
            
            assert len(klines) == 2
            assert isinstance(klines[0], Kline)
            assert klines[0].open == 65000.0
            assert klines[1].close == 65600.0
            
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_klines_raises_exception(self, exchange):
        """测试API失败时抛出异常"""
        with patch.object(exchange, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API请求失败"):
                await exchange.get_klines("BTCUSDT", "4h", limit=10)
    
    @pytest.mark.asyncio
    async def test_get_ticker_success(self, exchange):
        """测试成功获取Ticker"""
        with patch.object(exchange, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_TICKER_DATA
            
            ticker = await exchange.get_ticker("BTCUSDT")
            
            assert isinstance(ticker, Ticker)
            assert ticker.symbol == "BTCUSDT"
            assert ticker.last_price == 65500.0
    
    @pytest.mark.asyncio
    async def test_get_funding_rate(self, exchange):
        """测试获取资金费率"""
        with patch.object(exchange, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = MOCK_FUNDING_DATA
            
            funding = await exchange.get_funding_rate("BTCUSDT")
            
            assert isinstance(funding, FundingRate)
            assert funding.symbol == "BTCUSDT"
            assert funding.funding_rate == 0.0001


# ============================================================
# DataFetcher测试
# ============================================================

class TestDataFetcher:
    """测试DataFetcher类"""
    
    @pytest.fixture
    def fetcher(self):
        """创建数据获取器实例"""
        return DataFetcher()
    
    def test_get_exchange_default(self, fetcher):
        """测试获取默认交易所"""
        exchange = fetcher.get_exchange()
        assert isinstance(exchange, BinanceExchange)
    
    def test_get_exchange_invalid(self, fetcher):
        """测试获取无效交易所"""
        with pytest.raises(ValueError, match="不支持的交易所"):
            fetcher.get_exchange("invalid_exchange")
    
    @pytest.mark.asyncio
    async def test_get_market_data(self, fetcher):
        """测试获取完整市场数据"""
        with patch.object(fetcher, 'get_klines', new_callable=AsyncMock) as mock_klines, \
             patch.object(fetcher, 'get_ticker', new_callable=AsyncMock) as mock_ticker, \
             patch.object(fetcher, 'get_funding_rate', new_callable=AsyncMock) as mock_funding:
            
            mock_klines.return_value = [
                Kline(1704067200000, 65000, 65500, 64800, 65200, 1000)
            ]
            mock_ticker.return_value = Ticker(
                "BTCUSDT", 65500, 65499, 65501, 50000, 2.35, 66000, 64000
            )
            mock_funding.return_value = FundingRate(
                "BTCUSDT", 0.0001, 1704067200000, 65500
            )
            
            data = await fetcher.get_market_data("BTCUSDT", "4h", 10)
            
            assert data["symbol"] == "BTCUSDT"
            assert data["timeframe"] == "4h"
            assert len(data["klines"]) == 1
            assert data["ticker"] is not None
            assert data["funding"] is not None


class TestTimeframe:
    """测试时间周期枚举"""
    
    def test_timeframe_values(self):
        """测试时间周期值"""
        assert Timeframe.M1 == "1m"
        assert Timeframe.H1 == "1h"
        assert Timeframe.H4 == "4h"
        assert Timeframe.D1 == "1d"


# ============================================================
# 运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
