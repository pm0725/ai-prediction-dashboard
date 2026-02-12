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
    mark_price: float = 0.0  # B-CRIT-2 修复: 添加默认值，避免构造时 TypeError


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

COINGECKO_MAPPING = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "TRX": "tron",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "SHIB": "shiba-inu",
    "LTC": "litecoin",
    "UNI": "uniswap",
    "BCH": "bitcoin-cash",
    "NEAR": "near",
    "APT": "aptos",
    "QNT": "quant-network",
    "FIL": "filecoin",
    "ATOM": "cosmos",
    "IMX": "immutable-x",
    "ARB": "arbitrum",
    "OP": "optimism",
    "SUI": "sui"
}

class BaseExchange:
    """交易所基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout, trust_env=True)
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
        """发送HTTP请求 (带自动重试和会话重置)"""
        
        # 获取代理配置 (优先使用 HTTPS_PROXY)
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or \
                os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        
        # [Debug] 强制检查代理并应用兜底
        if not proxy:
            default_proxy = "http://127.0.0.1:7890"
            if "binance" in url: # 仅对需要翻墙的API应用兜底
                 proxy = default_proxy
            
        # 增加重试循环，处理连接断开或DNS污染问题
        for attempt in range(2):
            try:
                session = await self._get_session()
                
                if attempt == 0:
                     logger.debug(f"API请求 [{method}] {url.split('?')[0]} | Proxy: {proxy}")
                
                async with session.request(method, url, params=params, headers=headers, proxy=proxy) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        text = await resp.text()
                        logger.warning(f"API响应非200 ({resp.status}) | URL: {url} | Body: {text[:200]}")
                        
                        # 遇到 5xx 或 429 错误，抛出 ClientError 以触发重试
                        if 500 <= resp.status < 600 or resp.status == 429:
                             raise aiohttp.ClientError(f"Server Error {resp.status}")
                             
                        raise Exception(f"API错误: {resp.status} - {text}")

            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
                logger.warning(f"API请求失败 (Attempt {attempt+1}/2): {e} | URL: {url.split('?')[0]}")
                
                # 如果是连接层面的错误，尝试重置会话
                # 这对解决 'Connect call failed' (DNS污染/IP变更) 这一类问题至关重要
                if attempt == 0:
                    logger.warning(">>> 检测到连接/网络异常，正在重置会话并重试...")
                    if self._session and not self._session.closed:
                        await self._session.close()
                    self._session = None # 强制下次重建会话
                    # 稍微等待一下
                    await asyncio.sleep(0.5)
                    continue
                
                # 第二次也失败，抛出最终异常
                raise Exception(f"API请求最终失败: {e}")
    
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
        klines, ticker, funding, fundamentals = await asyncio.gather(
            self.get_klines(symbol, timeframe, kline_limit),
            self.get_ticker(symbol),
            self.get_funding_rate(symbol),
            self.get_token_fundamentals(symbol),
            return_exceptions=True
        )
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "klines": klines if not isinstance(klines, Exception) else [],
            "ticker": ticker if not isinstance(ticker, Exception) else None,
            "funding": funding if not isinstance(funding, Exception) else None,
            "fundamental_data": fundamentals if not isinstance(fundamentals, Exception) else None,
            "timestamp": datetime.now().isoformat()
        }
        
    async def get_token_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取代币基本面数据 (CoinGecko)
        
        Args:
            symbol: 交易对符号 (e.g., "BTCUSDT")
            
        Returns:
            dict: 基本面数据 or None
        """
        # 1. 解析基础币种
        base_asset = normalize_symbol(symbol).replace("USDT", "").replace("USDC", "")
        if base_asset == "BTC": base_asset = "BTC" # Normalized as BTCUSDT -> BTC
        
        # 2. 映射 ID
        cg_id = COINGECKO_MAPPING.get(base_asset)
        if not cg_id:
            logger.debug(f"未找到 {base_asset} 的 CoinGecko ID映射")
            return None
            
        # 3. 调用 API
        # CoinGecko 免费 API (无需Key, 30 req/min)
        url = f"https://api.coingecko.com/api/v3/coins/{cg_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true",
            "sparkline": "false"
        }
        
        try:
            # 使用临时 Session 或复用 BaseExchange 的 Session (这里简化直接用 aiohttp)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5.0) as response:
                    if response.status == 429:
                        logger.warning("CoinGecko API 限流 (429)")
                        return None
                    if response.status != 200:
                        logger.warning(f"CoinGecko API 错误: {response.status}")
                        return None
                        
                    data = await response.json()
                    
                    # 4. 提取关键字段
                    market_data = data.get("market_data", {})
                    
                    return {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "sentiment_votes_up_percentage": data.get("sentiment_votes_up_percentage"),
                        "community_score": data.get("community_score"),
                        "developer_score": data.get("developer_score"),
                        "public_interest_score": data.get("public_interest_score"),
                        "total_volume": market_data.get("total_volume", {}).get("usd"),
                        "market_cap": market_data.get("market_cap", {}).get("usd"),
                        "ath_change_percentage": market_data.get("ath_change_percentage", {}).get("usd"),
                        "price_change_24h": market_data.get("price_change_percentage_24h")
                    }
                    
        except Exception as e:
            logger.error(f"获取 {base_asset} 基本面数据失败: {e}")
            return None


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
