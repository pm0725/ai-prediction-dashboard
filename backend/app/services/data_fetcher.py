"""
智链预测 - 数据获取模块
========================
从交易所API获取实时市场数据
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
import json
import os
import re

logger = logging.getLogger(__name__)


# ============================================================
# 数据模型
# ============================================================

class Timeframe(str, Enum):
    """K线周期"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


@dataclass
class Kline:
    """K线数据"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float = 0.0
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def change_percent(self) -> float:
        if self.open == 0:
            return 0
        return ((self.close - self.open) / self.open) * 100


@dataclass
class Ticker:
    """行情快照"""
    symbol: str
    last_price: float
    bid_price: float
    ask_price: float
    volume_24h: float
    change_24h: float
    high_24h: float
    low_24h: float
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


@dataclass
class FundingRate:
    """资金费率"""
    symbol: str
    funding_rate: float
    funding_time: int
    mark_price: float


@dataclass
class OpenInterest:
    """持仓量"""
    symbol: str
    open_interest: float
    open_interest_value: float
    timestamp: int


@dataclass
class OrderBook:
    """订单簿摘要"""
    symbol: str
    bid_ask_ratio: float
    total_bid_volume: float
    total_ask_volume: float
    major_support: Dict[str, float]  # {price, volume}
    major_resistance: Dict[str, float] # {price, volume}
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


def normalize_symbol(symbol: str) -> str:
    """
    归一化交易对符号 (同步 data_aggregator 中的逻辑)
    """
    if not symbol:
        return ""
    
    s = symbol.upper()
    s = re.sub(r'[-/_.]', '', s)
    
    special_map = {
        "PEPE": "1000PEPE", "SHIB": "1000SHIB", "LUNC": "1000LUNC",
        "XEC": "1000XEC", "FLOKI": "1000FLOKI", "BONK": "1000BONK",
        "RATS": "1000RATS", "SATS": "1000SATS"
    }
    
    base = s
    if s.endswith("USDT"):
        base = s[:-4]
    
    check_base = base.replace("1000", "")
    
    if check_base in special_map:
        s = special_map[check_base] + "USDT"
    elif not s.endswith("USDT"):
        s = f"{s}USDT"
        
    return s


# ============================================================
# 交易所基类
# ============================================================

class BaseExchange:
    """交易所基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """发送HTTP请求"""
        """发送HTTP请求"""
        session = await self._get_session()
        
        # 获取代理配置
        proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        
        try:
            async with session.request(method, url, params=params, headers=headers, proxy=proxy) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    text = await resp.text()
                    logger.error(f"API请求失败 ({url}): {resp.status} - {text}")
                    raise Exception(f"API错误: {resp.status} - {text}")
        except asyncio.TimeoutError:
            logger.error(f"API请求超时: {url}")
            raise Exception("请求超时")
    
    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[Kline]:
        raise NotImplementedError
    
    async def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError
    
    async def get_funding_rate(self, symbol: str) -> FundingRate:
        raise NotImplementedError

    async def get_order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        raise NotImplementedError


# ============================================================
# Binance实现
# ============================================================

class BinanceExchange(BaseExchange):
    """Binance交易所API"""
    
    BASE_URL = "https://fapi.binance.com"  # 合约API
    SPOT_URL = "https://api.binance.com"
    
    def __init__(self):
        super().__init__("binance")
    
    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[Kline]:
        """获取K线数据"""
        symbol = normalize_symbol(symbol)
        url = f"{self.BASE_URL}/fapi/v1/klines"
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "limit": limit
        }
        
        try:
            data = await self._request("GET", url, params=params)
            klines = []
            for item in data:
                klines.append(Kline(
                    timestamp=item[0],
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                    quote_volume=float(item[7])
                ))
            return klines
        except Exception as e:
            logger.error(f"获取K线失败: {e}")
            raise Exception(f"API请求失败: {e}")
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """获取行情快照"""
        url = f"{self.BASE_URL}/fapi/v1/ticker/24hr"
        params = {"symbol": symbol}
        
        try:
            data = await self._request("GET", url, params=params)
            return Ticker(
                symbol=symbol,
                last_price=float(data["lastPrice"]),
                bid_price=float(data.get("bidPrice", data["lastPrice"])),
                ask_price=float(data.get("askPrice", data["lastPrice"])),
                volume_24h=float(data["volume"]),
                change_24h=float(data["priceChangePercent"]),
                high_24h=float(data["highPrice"]),
                low_24h=float(data["lowPrice"])
            )
        except Exception as e:
            logger.error(f"获取Ticker失败 [{symbol}]: {e}")
            raise Exception(f"API请求失败 ({symbol}): {e}")
    
    async def get_funding_rate(self, symbol: str) -> FundingRate:
        """获取资金费率"""
        url = f"{self.BASE_URL}/fapi/v1/fundingRate"
        params = {"symbol": symbol, "limit": 1}
        
        try:
            data = await self._request("GET", url, params=params)
            if data:
                item = data[0]
                return FundingRate(
                    symbol=symbol,
                    funding_rate=float(item["fundingRate"]),
                    funding_time=int(item["fundingTime"]),
                )
        except Exception as e:
            logger.error(f"获取资金费率失败: {e}")
            raise Exception(f"API请求失败: {e}")
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        """获取订单簿并计算摘要"""
        symbol = normalize_symbol(symbol)
        url = f"{self.BASE_URL}/fapi/v1/depth"
        params = {"symbol": symbol, "limit": limit}
        
        try:
            data = await self._request("GET", url, params=params)
            
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            
            # 计算买盘总量
            total_bid_vol = sum(float(b[1]) for b in bids)
            
            # 计算卖盘总量
            total_ask_vol = sum(float(a[1]) for a in asks)
            
            # 计算多空比
            ratio = total_bid_vol / total_ask_vol if total_ask_vol > 0 else 1.0
            
            # 寻找最大支撑 (买单中量最大的)
            max_bid = max(bids, key=lambda x: float(x[1])) if bids else [0, 0]
            major_support = {"price": float(max_bid[0]), "volume": float(max_bid[1])}
            
            # 寻找最大阻力 (卖单中量最大的)
            max_ask = max(asks, key=lambda x: float(x[1])) if asks else [0, 0]
            major_resistance = {"price": float(max_ask[0]), "volume": float(max_ask[1])}
            
            return OrderBook(
                symbol=symbol,
                bid_ask_ratio=round(ratio, 4),
                total_bid_volume=round(total_bid_vol, 4),
                total_ask_volume=round(total_ask_vol, 4),
                major_support=major_support,
                major_resistance=major_resistance
            )
            
        except Exception as e:
            logger.error(f"获取订单簿失败: {e}")
            raise Exception(f"API请求失败: {e}")
    
    async def get_open_interest(self, symbol: str) -> OpenInterest:
        """获取持仓量"""
        url = f"{self.BASE_URL}/fapi/v1/openInterest"
        params = {"symbol": symbol}
        
        try:
            data = await self._request("GET", url, params=params)
            return OpenInterest(
                symbol=symbol,
                open_interest=float(data["openInterest"]),
                open_interest_value=0,
                timestamp=int(data["time"])
            )
        except Exception as e:
            logger.error(f"获取持仓量失败: {e}")
            raise Exception(f"API请求失败: {e}")
    



# ============================================================
# 数据获取器
# ============================================================

class DataFetcher:
    """统一数据获取器"""
    
    def __init__(self):
        self.exchanges: Dict[str, BaseExchange] = {
            "binance": BinanceExchange()
        }
        self.default_exchange = "binance"
    
    async def close(self):
        """关闭所有连接"""
        for exchange in self.exchanges.values():
            await exchange.close()
    
    def get_exchange(self, name: Optional[str] = None) -> BaseExchange:
        """获取交易所实例"""
        name = name or self.default_exchange
        if name not in self.exchanges:
            raise ValueError(f"不支持的交易所: {name}")
        return self.exchanges[name]
    
    async def get_klines(
        self,
        symbol: str,
        timeframe: str = "4h",
        limit: int = 100,
        exchange: Optional[str] = None
    ) -> List[Kline]:
        """获取K线数据"""
        ex = self.get_exchange(exchange)
        return await ex.get_klines(symbol, timeframe, limit)
    
    async def get_ticker(
        self,
        symbol: str,
        exchange: Optional[str] = None
    ) -> Ticker:
        """获取行情快照"""
        ex = self.get_exchange(exchange)
        return await ex.get_ticker(symbol)
    
    async def get_funding_rate(
        self,
        symbol: str,
        exchange: Optional[str] = None
    ) -> FundingRate:
        """获取资金费率"""
        ex = self.get_exchange(exchange)
        return await ex.get_funding_rate(symbol)
        
    async def get_order_book(
        self,
        symbol: str,
        limit: int = 20,
        exchange: Optional[str] = None
    ) -> OrderBook:
        """获取订单簿摘要"""
        ex = self.get_exchange(exchange)
        return await ex.get_order_book(symbol, limit)
    
    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "4h",
        kline_limit: int = 50
    ) -> Dict[str, Any]:
        """获取完整市场数据"""
        # 并发获取所有数据
        klines, ticker, funding = await asyncio.gather(
            self.get_klines(symbol, timeframe, kline_limit),
            self.get_ticker(symbol),
            self.get_funding_rate(symbol),
            return_exceptions=True
        )
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "klines": klines if not isinstance(klines, Exception) else [],
            "ticker": ticker if not isinstance(ticker, Exception) else None,
            "funding": funding if not isinstance(funding, Exception) else None,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================
# 单例和工厂函数
# ============================================================

_fetcher_instance: Optional[DataFetcher] = None


def get_data_fetcher() -> DataFetcher:
    """获取数据获取器单例"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = DataFetcher()
    return _fetcher_instance


async def get_async_fetcher() -> DataFetcher:
    """异步获取（用于依赖注入）"""
    return get_data_fetcher()
