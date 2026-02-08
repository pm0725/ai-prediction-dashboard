"""
智链预测 - 测试配置
==================
pytest配置和共享fixtures
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_kline():
    """提供单个K线样本"""
    from app.services.data_fetcher import Kline
    return Kline(
        timestamp=1704067200000,
        open=65000.0,
        high=65500.0,
        low=64800.0,
        close=65200.0,
        volume=1000.0
    )


@pytest.fixture
def sample_ticker():
    """提供Ticker样本"""
    from app.services.data_fetcher import Ticker
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
def mock_api_key(monkeypatch):
    """模拟API密钥环境变量"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-api-key-12345")
