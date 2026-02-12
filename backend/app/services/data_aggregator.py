# -*- coding: utf-8 -*-
"""
智链预测 - 数据聚合模块
=======================
市场数据获取,技术指标计算与AI上下文构建

此模块负责从外部数据源获取市场数据,计算技术指标,
并整合为适合AI分析的结构化上下文.

主要功能:
1. 从Binance API获取K线数据
2. 计算技术指标(MA,RSI,MACD等)
3. 模拟新闻数据获取
4. 将所有数据整合为AI Prompt上下文

Author: 智链预测团队
Version: 1.0.0
"""

import asyncio
import os
import re
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd
from loguru import logger

# 尝试导入可选依赖
try:
    from binance import AsyncClient, Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    logger.warning("python-binance 未安装,将使用模拟数据")

try:
    import ta
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.trend import MACD, EMAIndicator, SMAIndicator
    from ta.volatility import BollingerBands, AverageTrueRange
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logger.warning("ta 库未安装,技术指标计算将使用简化版本")

from app.models.indicators import TechnicalIndicators


# ============================================================
# 数据缓存层 (TTL Cache)
# ============================================================
import time as _time

class DataCache:
    """
    简易 TTL 数据缓存
    
    用于避免短时间内重复请求相同的 API 数据。
    线程安全 (通过 asyncio.Lock)。
    """
    def __init__(self, default_ttl: int = 30):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._store:
                ts, val = self._store[key]
                if _time.time() - ts < self._ttl:
                    return val
                del self._store[key]
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        async with self._lock:
            self._store[key] = (_time.time(), value)
    
    async def clear(self):
        async with self._lock:
            self._store.clear()

# 全局缓存实例
_data_cache = DataCache(default_ttl=30)

# 全局 BinanceDataFetcher 单例
_global_fetcher: Optional[Any] = None
_global_fetcher_lock = asyncio.Lock()

async def get_global_fetcher(api_key: str = "", api_secret: str = ""):
    """获取全局 BinanceDataFetcher 单例 (避免每次重建连接)"""
    global _global_fetcher
    async with _global_fetcher_lock:
        if _global_fetcher is None:
            _global_fetcher = BinanceDataFetcher(api_key, api_secret)
        return _global_fetcher


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class KlineData:
    """K线数据结构"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int





@dataclass
class MarketContext:
    """完整的市场上下文,用于AI分析"""
    symbol: str
    current_price: float
    kline_summary: str
    klines: list[dict]  # 新增:原始K线数据
    indicators: TechnicalIndicators
    funding_rate: Optional[float]
    open_interest: Optional[float]
    news_headlines: list[str]
    market_sentiment: str
    timeframe: str = "4h"  # 分析周期
    
    # 新增字段
    order_book: Optional[dict] = None          # 订单簿摘要
    trend_kline_summary: Optional[str] = None  # 趋势周期K线摘要
    trend_klines: Optional[list[dict]] = None  # 趋势周期原始K线
    trend_indicators: Optional[TechnicalIndicators] = None # 趋势周期指标
    fundamental_data: Optional[dict] = None    # 基本面数据 (CoinGecko)
    fear_greed_index: Optional[dict] = None    # 恐惧贪婪指数
    
    # 新增: 机构级预警字段
    volatility_score: float = 0.0              # 0-100 波动率风险分
    whale_activity: Optional[dict] = None      # 巨鲸活动分析
    liquidity_gaps: list = None                # 订单簿真空区
    
    # 新增: 传统技术支撑/阻力 (Traditional TA)
    pivot_points: Optional[dict] = None        # Pivot Points
    swing_levels: Optional[dict] = None        # Swing Highs/Lows
    
    # 新增: 多空比/历史费率/BTC上下文
    long_short_ratio: Optional[float] = None   # 多空持仓人数比
    funding_rate_history: Optional[dict] = None # 历史资金费率序列与趋势
    btc_context: Optional[dict] = None         # BTC 大盘上下文 (山寨币用)
    volume_ratio: float = 1.0                  # 相对成交量

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式,供AI分析使用"""
        data = {
            "timeframe": self.timeframe,  # 分析周期
            "kline_summary": self.kline_summary,
            "current_price": self.current_price,
            "funding_rate": self.funding_rate,
            "open_interest": self.open_interest,
            "rsi": self.indicators.rsi_14,
            "macd": self._format_macd(),
            "ma_status": self._format_ma_status(),
            "ema_status": self._format_ema_status(),  # 新增
            "bollinger": self._format_bollinger(),
            "atr": self.indicators.atr_14,  # ATR波动率
            "news_headlines": self.news_headlines,
            "market_sentiment": self.market_sentiment,
            # ADX 趋势强度
            "adx": self.indicators.adx,
            "adx_status": self.indicators.adx_status,
            # VWAP
            "vwap": self.indicators.vwap,
            "vwap_deviation": self.indicators.vwap_deviation,
            # 新增: K线形态和信号冲突
            "candlestick_patterns": self.indicators.candlestick_patterns,
            "signal_conflicts": self.indicators.signal_conflicts,
            # 新增: 趋势线
            "trend_lines": self.indicators.trend_lines,
            # 新增: 机构预警
            "volatility_score": self.volatility_score,
            "whale_activity": self.whale_activity,
            "liquidity_gaps": self.liquidity_gaps,
            # 新增: TA S/R
            "pivot_points": self.pivot_points,
            "swing_levels": self.swing_levels
        }
        
        # 注入订单簿
        if self.order_book:
            data["order_book"] = self.order_book
            
        # 注入趋势周期数据
        if self.trend_kline_summary:
            data["trend_context"] = {
                "summary": self.trend_kline_summary,
                "rsi": self.trend_indicators.rsi_14 if self.trend_indicators else None,
                "trend_status": self.trend_indicators.trend_status if self.trend_indicators else None,
                # New fields for Trend Alignment
                "ema_21": self.trend_indicators.ema_21 if self.trend_indicators else None,
                "bb_width": self.trend_indicators.bb_width if self.trend_indicators else None,
                "bb_width": self.trend_indicators.bb_width if self.trend_indicators else None,
                "candlestick_patterns": self.trend_indicators.candlestick_patterns if self.trend_indicators else []
            }
            if self.trend_klines:
                data["trend_context"]["klines"] = self.trend_klines
        
        # 注入恐惧贪婪指数
        if self.fear_greed_index:
            data["fear_greed_index"] = self.fear_greed_index
            
        # 注入理论清算价格
        data["liquidation_levels"] = self._calculate_liquidation_levels()
        
        # 注入多空比
        if self.long_short_ratio is not None:
            data["long_short_ratio"] = self.long_short_ratio
        
        # 注入历史资金费率趋势
        if self.funding_rate_history:
            data["funding_rate_history"] = self.funding_rate_history
        
        # 注入BTC上下文 (山寨币分析时)
        if self.btc_context:
            data["btc_context"] = self.btc_context
        
        # 注入相对成交量
        data["volume_ratio"] = self.volume_ratio
            
        # ========== V2.0 Pro: SMC & VPVR ==========
        data["vpvr"] = {
            "poc_hvn": self.indicators.vp_hvn, # 成交密集区
            "vacuum_lvn": self.indicators.vp_lvn # 成交真空区
        }
        data["smc"] = {
            "order_blocks": self.indicators.order_blocks, # 机构订单块
            "fvg_gaps": self.indicators.fvg_gaps # 价格缺口
        }
        
        return data
    
    def _format_macd(self) -> str:
        """格式化MACD描述"""
        hist = self.indicators.macd_histogram
        if hist > 0 and self.indicators.macd_line > self.indicators.macd_signal:
            return f"MACD金叉,柱状图为正({hist:.4f}),多头动能增强"
        elif hist < 0 and self.indicators.macd_line < self.indicators.macd_signal:
            return f"MACD死叉,柱状图为负({hist:.4f}),空头动能增强"
        elif hist > 0:
            return f"MACD柱状图为正({hist:.4f}),但动能减弱"
        else:
            return f"MACD柱状图为负({hist:.4f}),但动能减弱"
    
    def _format_ma_status(self) -> str:
        """格式化均线状态"""
        ind = self.indicators
        status = []
        
        if self.current_price > ind.sma_20:
            status.append(f"价格站上MA20({ind.sma_20:.2f})")
        else:
            status.append(f"价格跌破MA20({ind.sma_20:.2f})")
        
        if ind.sma_20 > ind.sma_50:
            status.append(f"MA20上穿MA50,{ind.ma_cross_status}")
        else:
            status.append(f"MA20下穿MA50,{ind.ma_cross_status}")
        
        return ",".join(status)
    
    def _format_bollinger(self) -> str:
        """格式化布林带状态"""
        ind = self.indicators
        price = self.current_price
        
        if price > ind.bb_upper:
            position = "突破上轨,超买"
        elif price < ind.bb_lower:
            position = "跌破下轨,超卖"
        elif price > ind.bb_middle:
            position = "位于中轨上方"
        else:
            position = "位于中轨下方"
        
        return f"{position},带宽: {ind.bb_width:.2%}"
    
    def _format_ema_status(self) -> str:
        """格式化EMA 9/21状态"""
        ind = self.indicators
        status = []
        
        # EMA交叉状态
        status.append(f"EMA9({ind.ema_9:.2f}) vs EMA21({ind.ema_21:.2f})")
        status.append(ind.ema_cross_status)
        
        # 价格与EMA关系
        if self.current_price > ind.ema_9 > ind.ema_21:
            status.append("价格>EMA9>EMA21,强势多头")
        elif self.current_price < ind.ema_9 < ind.ema_21:
            status.append("价格<EMA9<EMA21,强势空头")
        elif ind.ema_9 > ind.ema_21:
            status.append("EMA多头排列")
        else:
            status.append("EMA空头排列")
        
        return ",".join(status)

    def _calculate_liquidation_levels(self) -> dict:
        """
        计算理论清算价格区间 (基于常见杠杆倍数)
        
        估算模型:
        - 20x杠杆: 维持保证金率约 0.5% -> 波动 -4.5% 爆仓
        - 50x杠杆: 维持保证金率约 1.0% -> 波动 -1.5% 爆仓
        - 100x杠杆: 维持保证金率约 2.0% -> 波动 -0.5% 爆仓 (极高风险)
        """
        price = self.current_price
        
        # 多头爆仓价 (下跌)
        long_liq_20x = price * (1 - 0.045)
        long_liq_50x = price * (1 - 0.015)
        long_liq_100x = price * (1 - 0.005)
        
        # 空头爆仓价 (上涨)
        short_liq_20x = price * (1 + 0.045)
        short_liq_50x = price * (1 + 0.015)
        short_liq_100x = price * (1 + 0.005)
        
        return {
            "long_liq": {
                "20x": float(f"{long_liq_20x:.2f}"),
                "50x": float(f"{long_liq_50x:.2f}"),
                "100x": float(f"{long_liq_100x:.2f}")
            },
            "short_liq": {
                "20x": float(f"{short_liq_20x:.2f}"),
                "50x": float(f"{short_liq_50x:.2f}"),
                "100x": float(f"{short_liq_100x:.2f}")
            }
        }


# ============================================================
# 外部情绪数据
# ============================================================

async def get_fear_greed_index(session: Optional[Any] = None) -> dict:
    """
    获取恐惧贪婪指数 (Fear & Greed Index)
    
    数据源: alternative.me (免费API)
    
    Returns:
        dict: {
            "value": 25,           # 0-100
            "classification": "极度恐惧",  # 中文分类
            "timestamp": "2024-01-01"
        }
    """
    import aiohttp
    

    
    session_owner = False
    if session is None:
        session = aiohttp.ClientSession()
        session_owner = True
        
    # 获取代理配置 (优先使用 HTTPS_PROXY)
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or \
            os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or \
            "http://127.0.0.1:7890"

    try:
        async with session.get(
            "https://api.alternative.me/fng/?limit=1",
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data"):
                        fng = data["data"][0]
                        value = int(fng["value"])
                        
                        # 中文分类
                        if value <= 25:
                            classification = "极度恐惧"
                        elif value <= 45:
                            classification = "恐惧"
                        elif value <= 55:
                            classification = "中性"
                        elif value <= 75:
                            classification = "贪婪"
                        else:
                            classification = "极度贪婪"
                        
                        return {
                            "value": value,
                            "classification": classification,
                            "timestamp": fng.get("timestamp", "")
                        }
    except Exception as e:
        logger.debug(f"获取恐惧贪婪指数失败: {e}")
    finally:
        if session_owner and session:
            await session.close()
    
    return {"value": 50, "classification": "中性", "timestamp": ""}


async def get_crypto_news(symbol: str = "BTC", session: Optional[Any] = None) -> list[str]:
    """
    获取加密货币新闻 (CryptoPanic 免费API)
    
    Returns:
        list[str]: 新闻标题列表 (最多5条)
    """
    import aiohttp
    
    # 提取币种名 (BTCUSDT -> BTC)
    coin = symbol.replace("USDT", "").replace("usdt", "").replace("1000", "")
    
    api_key = os.getenv("CRYPTOPANIC_API_KEY", "")
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or \
            os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or None
    
    session_owner = session is None
    _session = session or aiohttp.ClientSession()
    
    try:
        if api_key:
            # 使用 CryptoPanic API
            url = "https://cryptopanic.com/api/free/v1/posts/"
            params = {
                "auth_token": api_key,
                "currencies": coin,
                "kind": "news",
                "filter": "important",
                "public": "true"
            }
            try:
                async with _session.get(url, params=params, proxy=proxy, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        headlines = []
                        for post in results[:5]:
                            title = post.get("title", "")
                            votes = post.get("votes", {})
                            sentiment = votes.get("positive", 0) - votes.get("negative", 0)
                            sentiment_label = "👍" if sentiment > 0 else ("👎" if sentiment < 0 else "")
                            headlines.append(f"{title} {sentiment_label}".strip())
                        return headlines
            except Exception as e:
                logger.debug(f"CryptoPanic API 失败: {e}")
        
        # 无API Key时回退到 CoinGecko 热搜趋势 (无需key)
        try:
            alt_url = "https://api.coingecko.com/api/v3/search/trending"
            async with _session.get(alt_url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    trending = data.get("coins", [])[:5]
                    headlines = [
                        f"{c['item']['name']}({c['item']['symbol']}) 热度排名#{c['item'].get('market_cap_rank') or 'N/A'}"
                        for c in trending
                    ]
                    return headlines
        except Exception as e:
            logger.debug(f"CoinGecko 热搜获取失败: {e}")
    except Exception:
        pass
    finally:
        if session_owner and _session:
            await _session.close()
    
    return []


async def get_global_market_stats() -> dict:
    """
    获取全局市场统计数据 (用于仪表盘概览)
    
    聚合恐惧贪婪指数、全场涨跌幅代理以及板块表现。
    """
    # 1. 获取恐惧贪婪指数
    fng = await get_fear_greed_index()
    
    # 2. 获取样板币种行情作为全场代理
    sectors_config = {
        "Layer 1": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"],
        "DeFi": ["LINKUSDT", "UNIUSDT", "AAVEUSDT", "MKRUSDT"],
        "Layer 2": ["MATICUSDT", "OPUSDT", "ARBUSDT"],
        "Meme": ["DOGEUSDT", "SHIBUSDT", "1000PEPEUSDT"]
    }
    
    all_symbols = []
    for syms in sectors_config.values():
        all_symbols.extend(syms)
    all_symbols = list(set(all_symbols))
    
    fetcher = BinanceDataFetcher()
    tickers = await fetcher.get_tickers(all_symbols)
    ticker_map = {t["symbol"]: t for t in tickers}
    
    # 3. 计算板块表现
    sector_performance = []
    total_change = 0
    count = 0
    
    for sector, syms in sectors_config.items():
        sector_changes = [ticker_map[s]["change_percent"] for s in syms if s in ticker_map]
        if sector_changes:
            avg_change = sum(sector_changes) / len(sector_changes)
            sector_performance.append({
                "name": sector,
                "change": round(avg_change, 2)
            })
            total_change += sum(sector_changes)
            count += len(sector_changes)
            
    # 4. 估算全场表现 (代理)
    market_change = round(total_change / count, 2) if count > 0 else 0.0
    
    # 5. 生成关键事件 (Dynamic Key Events)
    key_events = []
    
    # Event 1: 情绪报警
    if fng["value"] >= 75:
        key_events.append({
            "time": "NOW", "category": "Macro", "type": "high",
            "title": f"市场进入极度贪婪状态 ({fng['value']})，注意风险"
        })
    elif fng["value"] <= 25:
        key_events.append({
            "time": "NOW", "category": "Macro", "type": "high",
            "title": f"市场进入极度恐慌状态 ({fng['value']})，寻找抄底机会"
        })
        
    # Event 2: 板块异动
    top_sector = max(sector_performance, key=lambda x: x["change"]) if sector_performance else None
    if top_sector and abs(top_sector["change"]) > 3.0:
        action = "领涨" if top_sector["change"] > 0 else "领跌"
        key_events.append({
            "time": "1H", "category": "Project", "type": "medium",
            "title": f"{top_sector['name']} 板块{action}全场 ({top_sector['change']:+.1f}%)"
        })
        
    # Event 3: 全场大势
    if abs(market_change) > 2.0:
        trend = "普涨" if market_change > 0 else "普跌"
        key_events.append({
            "time": "4H", "category": "On-chain", "type": "medium",
            "title": f"加密市场出现{trend}行情，平均波动 {market_change:+.1f}%"
        })
        
    # 保底事件
    if not key_events:
        key_events.append({
            "time": "NOW", "category": "Macro", "type": "low",
            "title": "市场处于平稳震荡期，无重大宏观异动"
        })

    # 5. 组合结果
    return {
        "fear_greed": fng,
        "market_change": market_change,
        "sector_performance": sector_performance,
        "key_events": key_events, # Added
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# 数据获取函数
# ============================================================

class BinanceDataFetcher:
    """
    Binance数据获取器
    
    从Binance API获取K线, 资金费率等数据
    """
    
    def __init__(self, api_key: str = "", api_secret: str = ""):
        """
        初始化数据获取器
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.client: Optional[AsyncClient] = None # 复用的客户端实例
        
        # 不再在init中创建连接,而是按需创建异步连接
        if not BINANCE_AVAILABLE:
            logger.warning("python-binance 未安装,无法获取真实数据")
    
    async def start_session(self):
        """显式启动长连接会话(用于高频场景)"""
        if not BINANCE_AVAILABLE:
            return
        if self.client is None:
            self.client = await self._create_new_client()
            logger.info("BinanceDataFetcher: 长连接会话已启动")
        return self.client
    
    async def get_token_fundamentals(self, symbol: str) -> Optional[dict]:
        """
        获取代币基本面数据 (CoinGecko) - Ported from DataFetcher
        """
        # 1. 简易映射表 (局部定义以避免全局污染)
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
        }
        
        # 2. 解析基础币种
        base_asset = symbol.replace("USDT", "").replace("USDC", "")
        if base_asset == "BTC": base_asset = "BTC"
        
        cg_id = COINGECKO_MAPPING.get(base_asset)
        if not cg_id:
            return None
            
        # 3. 调用 API
        import aiohttp
        url = f"https://api.coingecko.com/api/v3/coins/{cg_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true",
            "sparkline": "false"
        }
        
        # 使用临时 session 或复用 data_fetcher 的 session 逻辑
        # 这里简单起见使用临时 session
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or \
                os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or None
                
        # 简单重试机制 (处理 429)
        import asyncio
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, proxy=proxy, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 429:
                            if attempt < 2:
                                wait_time = 2 * (attempt + 1)
                                logger.warning(f"CoinGecko API 限流 (429), 等待 {wait_time}s 重试...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logger.warning("CoinGecko API 限流 (429), 重试次数耗尽")
                                return None
                                
                        if response.status == 200:
                            data = await response.json()
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
                        else:
                            logger.warning(f"CoinGecko API 错误: {response.status}")
                            return None
            except Exception as e:
                logger.debug(f"基本面获取失败({symbol}): {e}")
                return None
            
        return None

    async def close_session(self):
        """关闭长连接会话"""
        if self.client:
            await self.client.close_connection()
            self.client = None
            logger.info("BinanceDataFetcher 长连接会话已关闭")

    async def _create_new_client(self) -> Optional[AsyncClient]:
        """创建新的客户端实例 (内部使用)"""
        if not BINANCE_AVAILABLE:
            return None
            
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or \
                os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or \
                "http://127.0.0.1:7890"
        
        requests_params = {}
        if proxy:
            requests_params['proxies'] = {'http': proxy, 'https': proxy}
            logger.debug(f"Binance AsyncClient 创建中 | Proxy: {proxy}")
        
        # 设置超时 (如果库支持)
        requests_params['timeout'] = 10
            
        return await AsyncClient.create(self.api_key, self.api_secret, requests_params=requests_params)

    async def _get_client(self) -> Optional[AsyncClient]:
        """获取客户端 (优先复用长连接,否则创建临时连接)"""
        if self.client:
            return self.client
        return await self._create_new_client()
    
    async def _close_temp_client(self, client: AsyncClient):
        """关闭客户端 (仅当不是长连接时)"""
        if client != self.client:
            await client.close_connection()

    async def get_klines(
        self,
        symbol: str,
        interval: str = "4h",
        limit: int = 50
    ) -> pd.DataFrame:
        """
        获取K线数据
        """
        symbol = normalize_symbol(symbol)
        if not BINANCE_AVAILABLE:
             raise Exception(f"python-binance库未安装,无法获取真实数据")

        client = await self._get_client()
        try:
            klines = await client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 
                'taker_buy_volume', 'taker_buy_quote', 'ignore'
            ])
            
            # 类型转换
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = df[col].astype(float)
            df['trades'] = df['trades'].astype(int)
            
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Binance API错误 [{symbol}]: {e}")
            raise Exception(f"无法获取真实K线数据 ({symbol}): {e}")
        finally:
            if client:
                await self._close_temp_client(client)
    

    
    async def get_funding_rate(self, symbol: str) -> float:
        """获取当前资金费率"""
        symbol = normalize_symbol(symbol)
        if not BINANCE_AVAILABLE:
            return 0.0001
            
        client = await self._get_client()
        try:
            info = await client.futures_funding_rate(symbol=symbol, limit=1)
            if info:
                return float(info[0]['fundingRate'])
        except Exception as e:
            logger.debug(f"获取资金费率失败 (非关键): {e}")
        finally:
            if client:
                await self._close_temp_client(client)
        
        return 0.0001
    
    async def get_open_interest(self, symbol: str) -> float:
        """获取持仓量"""
        symbol = normalize_symbol(symbol)
        if not BINANCE_AVAILABLE:
            return 0.0
            
        client = await self._get_client()
        try:
            info = await client.futures_open_interest(symbol=symbol)
            return float(info['openInterest'])
        except Exception as e:
            logger.debug(f"获取持仓量失败 (非关键): {e}")
        finally:
            if client:
                await self._close_temp_client(client)
        
        return 0.0
    
    async def get_tickers(self, symbols: list[str]) -> list[dict]:
        """
        批量获取24小时价格变动数据 (优化版:单次API调用)
        """
        results = []
        if not BINANCE_AVAILABLE:
            return results
            
        client = await self._get_client()
        async def _fetch_single_ticker(sym):
            try:
                # API weight: 1
                return await client.futures_ticker(symbol=sym)
            except Exception as e:
                logger.warning(f"Fetch ticker failed for {sym}: {e}")
                return None

        try:
            # FIX 429: If symbols count is small, fetch individually to save weight
            # Single symbol weight = 1. All symbols weight = 40.
            # So if we have < 40 symbols, individual is theoretically cheaper/same, 
            # but for concurrency overhead, let's say < 10 is definitely better.
            if len(symbols) > 0 and len(symbols) <= 10:
                tasks = [_fetch_single_ticker(s) for s in symbols]
                results_raw = await asyncio.gather(*tasks)
                
                for t in results_raw:
                    if t:
                        results.append({
                            "symbol": t['symbol'],
                            "price": float(t['lastPrice']),
                            "change_percent": float(t['priceChangePercent']),
                            "quote_volume": float(t['quoteVolume'])
                        })
            else:
                # Fallback to fetching all tickers (Weight: 40)
                all_tickers = await client.futures_ticker()
                ticker_map = {t['symbol']: t for t in all_tickers}
                
                for symbol in symbols:
                    try:
                        if symbol in ticker_map:
                            t = ticker_map[symbol]
                            results.append({
                                "symbol": symbol,
                                "price": float(t['lastPrice']),
                                "change_percent": float(t['priceChangePercent']),
                                "quote_volume": float(t['quoteVolume'])
                            })
                    except Exception as e:
                        logger.error(f"解析Ticker数据失败 [{symbol}]: {e}")
                            
        except Exception as e:
            logger.error(f"获取Ticker最终失败: {e}")
            # 返回空列表而不是抛出异常，防止上层接口 500
            return []
                
        return results

    async def get_long_short_ratio(self, symbol: str) -> Optional[float]:
        """
        获取多空持仓人数比 (直接调用 Binance REST API，绕过 python-binance 版本限制)
        """
        symbol = normalize_symbol(symbol)
        
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or \
                os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or \
                "http://127.0.0.1:7890"
        
        url = f"https://fapi.binance.com/futures/data/topLongShortAccountRatio"
        params = {"symbol": symbol, "period": "5m", "limit": 1}
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, proxy=proxy, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data:
                            ratio = float(data[0]['longShortRatio'])
                            logger.debug(f"{symbol} 多空比: {ratio:.3f}")
                            return ratio
        except Exception as e:
            logger.debug(f"获取多空比失败 (非关键): {e}")
        return None

    async def get_funding_rate_history(self, symbol: str, limit: int = 24) -> list[dict]:
        """
        获取历史资金费率序列 (近 limit 期)
        用于判断费率趋势方向
        """
        symbol = normalize_symbol(symbol)
        if not BINANCE_AVAILABLE:
            return []
        
        client = await self._get_client()
        try:
            info = await client.futures_funding_rate(symbol=symbol, limit=limit)
            result = []
            for item in info:
                result.append({
                    "rate": float(item['fundingRate']),
                    "time": item.get('fundingTime', 0)
                })
            if result:
                rates = [r['rate'] for r in result]
                avg = sum(rates) / len(rates)
                recent_avg = sum(rates[-3:]) / min(3, len(rates))
                trend = "上升" if recent_avg > avg else ("下降" if recent_avg < avg else "平稳")
                logger.debug(f"{symbol} 资金费率趋势: {trend} (均值: {avg*100:.4f}%, 近期: {recent_avg*100:.4f}%)")
                return {
                    "current": rates[-1] if rates else 0,
                    "avg_24": avg,
                    "recent_avg": recent_avg,
                    "trend": trend,
                    "history": rates[-8:]  # 只传近8期给AI节省token
                }
        except Exception as e:
            logger.debug(f"获取历史资金费率失败: {e}")
        finally:
            if client:
                await self._close_temp_client(client)
        return {}

    async def get_order_book(self, symbol: str, limit: int = 100) -> dict:
        """
        获取订单簿深度并计算买卖墙 (增强版)
        
        增强分析:
        - 100档深度
        - 大单检测 (>5 BTC)
        - +/-1%范围内累积挂单量
        - 买卖压力失衡分析
        """
        symbol = normalize_symbol(symbol)
        if not BINANCE_AVAILABLE:
            return None
            
        client = await self._get_client()
        try:
            depth = await client.futures_order_book(symbol=symbol, limit=limit)
            
            bids = [[float(p), float(q)] for p, q in depth['bids']]
            asks = [[float(p), float(q)] for p, q in depth['asks']]
            
            if not bids or not asks:
                return None
            
            current_price = (bids[0][0] + asks[0][0]) / 2
            
            # 基础统计
            total_bid_vol = sum([q for _, q in bids])
            total_ask_vol = sum([q for _, q in asks])
            bid_ask_ratio = total_bid_vol / total_ask_vol if total_ask_vol > 0 else 0
            
            # ========== 新增: +/-1%范围内累积挂单量 ==========
            price_range_pct = 0.01  # 1%
            bid_1pct = sum([q for p, q in bids if p >= current_price * (1 - price_range_pct)])
            ask_1pct = sum([q for p, q in asks if p <= current_price * (1 + price_range_pct)])
            nearby_pressure = "buy_pressure" if bid_1pct > ask_1pct * 1.5 else ("sell_pressure" if ask_1pct > bid_1pct * 1.5 else "balanced")
            
            # ========== 新增: 大单检测 (>5 BTC) ==========
            large_order_threshold = 5.0
            large_bids = [{"price": p, "volume": q} for p, q in bids if q >= large_order_threshold]
            large_asks = [{"price": p, "volume": q} for p, q in asks if q >= large_order_threshold]
            
            # 寻找最大压力位
            if bids:
                max_bid_wall = max(bids, key=lambda x: x[1])
                major_support = {"price": max_bid_wall[0], "volume": max_bid_wall[1]}
            else:
                major_support = {"price": 0, "volume": 0}
            
            if asks:
                max_ask_wall = max(asks, key=lambda x: x[1])
                major_resistance = {"price": max_ask_wall[0], "volume": max_ask_wall[1]}
            else:
                major_resistance = {"price": 0, "volume": 0}
            
            return {
                "bid_ask_ratio": float(f"{bid_ask_ratio:.2f}"),
                "total_bid_volume": float(f"{total_bid_vol:.2f}"),
                "total_ask_volume": float(f"{total_ask_vol:.2f}"),
                "major_support": major_support,
                "major_resistance": major_resistance,
                # 新增字段
                "nearby_bid_1pct": float(f"{bid_1pct:.2f}"),
                "nearby_ask_1pct": float(f"{ask_1pct:.2f}"),
                "nearby_pressure": nearby_pressure,
                "large_bids": large_bids[:3],  # 最多3个大买单
                "large_asks": large_asks[:3],  # 最多3个大卖单
            }
        except Exception as e:
            logger.debug(f"获取订单簿失败 (非关键): {e}")
            return None
        finally:
            if client:
                await self._close_temp_client(client)

    async def get_agg_trades(self, symbol: str, limit: int = 1000) -> list[dict]:
        """
        获取近期逐笔成交 (AggTrades)
        用于分析巨鲸行为和CVD
        """
        symbol = normalize_symbol(symbol)
        if not BINANCE_AVAILABLE:
            return []
            
        client = await self._get_client()
        try:
            # 获取最近成交
            trades = await client.futures_aggregate_trades(symbol=symbol, limit=limit)
            return trades
        except Exception as e:
            logger.debug(f"获取逐笔成交失败 (非关键): {e}")
            return []
        finally:
            if client:
                await self._close_temp_client(client)


# ============================================================
# 技术指标计算
# ============================================================

def calculate_indicators(df: pd.DataFrame) -> TechnicalIndicators:
    """
    计算技术指标
    
    Args:
        df: 包含OHLCV数据的DataFrame
    
    Returns:
        TechnicalIndicators: 计算完成的技术指标对象
    """
    close = df['close']
    high = df['high']
    low = df['low']
    
    if TA_AVAILABLE:
        # 使用ta库计算
        sma_20 = SMAIndicator(close, window=20).sma_indicator().iloc[-1]
        sma_50 = SMAIndicator(close, window=min(50, len(df))).sma_indicator().iloc[-1]
        ema_12 = EMAIndicator(close, window=12).ema_indicator().iloc[-1]
        ema_26 = EMAIndicator(close, window=26).ema_indicator().iloc[-1]
        
        rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
        
        macd = MACD(close)
        macd_line = macd.macd().iloc[-1]
        macd_signal = macd.macd_signal().iloc[-1]
        macd_histogram = macd.macd_diff().iloc[-1]
        
        bb = BollingerBands(close, window=20, window_dev=2)
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_middle = bb.bollinger_mavg().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]
        bb_width = (bb_upper - bb_lower) / bb_middle
        
        atr = AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
    else:
        # 简化计算(不依赖ta库)
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(min(50, len(df))).mean().iloc[-1]
        ema_12 = close.ewm(span=12).mean().iloc[-1]
        ema_26 = close.ewm(span=26).mean().iloc[-1]
        
        # 优化RSI计算 (使用 Wilder's Smoothing / EMA)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))
        
        # Wilder's Smoothing (alpha = 1/N) 等同于 span = 2N - 1 的 EMA
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        
        # 避免除以零错误
        if avg_loss.iloc[-1] == 0:
            rsi = 100.0 if avg_gain.iloc[-1] > 0 else 50.0
        else:
            rs = avg_gain / avg_loss
            rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # 简化MACD (修复: 使用完整序列计算信号线)
        macd_series = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        macd_line = macd_series.iloc[-1]
        macd_signal = macd_series.ewm(span=9).mean().iloc[-1]
        macd_histogram = macd_line - macd_signal
        
        # 简化布林带
        bb_middle = sma_20
        std = close.rolling(20).std().iloc[-1]
        bb_upper = bb_middle + 2 * std
        bb_lower = bb_middle - 2 * std
        bb_width = (bb_upper - bb_lower) / bb_middle
        
        # 优化ATR计算 (使用 Wilder's Smoothing / EMA)
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        # Wilder's Smoothing alpha = 1/14
        atr = tr.ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
    
    # 判断趋势状态
    current_price = close.iloc[-1]
    if current_price > sma_20 > sma_50:
        trend_status = "bullish"
    elif current_price < sma_20 < sma_50:
        trend_status = "bearish"
    else:
        trend_status = "neutral"
    
    # 判断均线交叉
    prev_sma_20 = close.rolling(20).mean().iloc[-2] if len(df) > 20 else sma_20
    prev_sma_50 = close.rolling(min(50, len(df))).mean().iloc[-2] if len(df) > 50 else sma_50
    
    if sma_20 > sma_50 and prev_sma_20 <= prev_sma_50:
        ma_cross_status = "golden_cross"
    elif sma_20 < sma_50 and prev_sma_20 >= prev_sma_50:
        ma_cross_status = "death_cross"
    else:
        ma_cross_status = "多头排列" if sma_20 > sma_50 else "空头排列"
    
    # ========== 新增: EMA 9/21 双均线系统 ==========
    ema_9 = close.ewm(span=9).mean().iloc[-1]
    ema_21 = close.ewm(span=21).mean().iloc[-1]
    prev_ema_9 = close.ewm(span=9).mean().iloc[-2] if len(df) > 9 else ema_9
    prev_ema_21 = close.ewm(span=21).mean().iloc[-2] if len(df) > 21 else ema_21
    
    if ema_9 > ema_21 and prev_ema_9 <= prev_ema_21:
        ema_cross_status = "EMA金叉"
    elif ema_9 < ema_21 and prev_ema_9 >= prev_ema_21:
        ema_cross_status = "EMA死叉"
    else:
        ema_cross_status = "EMA多头" if ema_9 > ema_21 else "EMA空头"
    
    # ========== 新增: K线形态识别 ==========
    candlestick_patterns = _detect_candlestick_patterns(df)
    
    # ========== 新增: 信号冲突检测 ==========
    signal_conflicts = _detect_signal_conflicts(
        rsi=rsi, macd_histogram=macd_histogram, trend_status=trend_status,
        ema_cross_status=ema_cross_status, current_price=current_price,
        bb_upper=bb_upper, bb_lower=bb_lower
    )
    
    # ========== 新增: 趋势线识别 ==========
    trend_lines = _detect_trend_lines(df)
    
    # ========== 新增: 成交量分析 ==========
    vol = df['volume']
    vol_ma20 = vol.rolling(window=20).mean()
    current_vol = vol.iloc[-1]
    avg_vol = vol_ma20.iloc[-1]
    
    volume_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
    volume_status = "normal"
    if volume_ratio < 0.8: volume_status = "low"
    elif volume_ratio > 2.5: volume_status = "ultra_high"
    elif volume_ratio > 1.5: volume_status = "high"
    
    # ========== 新增: ADX 趋势强度 ==========
    adx_val = 0.0
    adx_status = "无趋势"
    try:
        if TA_AVAILABLE:
            from ta.trend import ADXIndicator
            adx_indicator = ADXIndicator(high, low, close, window=14)
            adx_val = _safe_float(adx_indicator.adx().iloc[-1], 0.0)
        else:
            # 简化 ADX 计算
            tr = pd.concat([
                high - low,
                abs(high - close.shift()),
                abs(low - close.shift())
            ], axis=1).max(axis=1)
            plus_dm = (high - high.shift()).clip(lower=0)
            minus_dm = (low.shift() - low).clip(lower=0)
            # 当 +DM < -DM 时 +DM=0，反之亦然
            mask = plus_dm < minus_dm
            plus_dm[mask] = 0
            minus_dm[~mask] = 0
            atr_s = tr.ewm(alpha=1/14, min_periods=14).mean()
            plus_di = 100 * (plus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr_s)
            minus_di = 100 * (minus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr_s)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
            adx_val = _safe_float(dx.ewm(alpha=1/14, min_periods=14).mean().iloc[-1], 0.0)
        
        if adx_val >= 25:
            adx_status = "强趋势"
        elif adx_val >= 20:
            adx_status = "弱趋势"
        else:
            adx_status = "无趋势"
    except Exception as e:
        logger.debug(f"ADX 计算失败: {e}")
    
    # ========== 新增: VWAP (成交量加权均价) ==========
    vwap_val = 0.0
    vwap_deviation = 0.0
    try:
        typical_price = (high + low + close) / 3
        cumulative_tpv = (typical_price * df['volume']).cumsum()
        cumulative_vol = df['volume'].cumsum()
        vwap_series = cumulative_tpv / cumulative_vol
        vwap_val = _safe_float(vwap_series.iloc[-1], current_price)
        if vwap_val > 0:
            vwap_deviation = (current_price - vwap_val) / vwap_val * 100
    except Exception as e:
        logger.debug(f"VWAP 计算失败: {e}")
    
    # ========== V2.0 Pro: SMC & VPVR ==========
    vp_data = _calculate_vpvr(df)
    smc_data = _detect_smc_indicators(df)
    
    return TechnicalIndicators(
        sma_20=_safe_float(sma_20),
        sma_50=_safe_float(sma_50),
        ema_12=_safe_float(ema_12),
        ema_26=_safe_float(ema_26),
        ema_9=_safe_float(ema_9),
        ema_21=_safe_float(ema_21),
        rsi_14=_safe_float(rsi, 50.0),
        macd_line=_safe_float(macd_line),
        macd_signal=_safe_float(macd_signal),
        macd_histogram=_safe_float(macd_histogram),
        bb_upper=_safe_float(bb_upper),
        bb_middle=_safe_float(bb_middle),
        bb_lower=_safe_float(bb_lower),
        bb_width=_safe_float(bb_width),
        atr_14=_safe_float(atr),
        trend_status=trend_status,
        ma_cross_status=ma_cross_status,
        ema_cross_status=ema_cross_status,
        candlestick_patterns=candlestick_patterns,
        signal_conflicts=signal_conflicts,
        trend_lines=trend_lines,
        volume_ratio=_safe_float(volume_ratio),
        volume_status=volume_status,
        adx=_safe_float(adx_val),
        adx_status=adx_status,
        vwap=_safe_float(vwap_val),
        vwap_deviation=round(_safe_float(vwap_deviation), 2),
        # V2.0 Pro fields
        vp_hvn=vp_data["hvn"],
        vp_lvn=vp_data["lvn"],
        order_blocks=smc_data["order_blocks"],
        fvg_gaps=smc_data["fvg_gaps"]
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为float,处理NaN和Inf"""
    try:
        val = float(value)
        if np.isnan(val) or np.isinf(val):
            return default
        return val
    except (ValueError, TypeError):
        return default


def _detect_trend_lines(df: pd.DataFrame) -> dict:
    """
    识别趋势线 (基于真正的局部极值 Pivot Point)
    
    算法:
    1. 识别最近K线中的局部高低点 (Pivot High/Low) — 逐K线对比前后N根
    2. 连接两个高点形成阻力线,连接两个低点形成支撑线
    3. 计算当前价格与趋势线的距离 (绝对值百分比)
    
    Returns:
        dict: {
            "resistance_line": {"slope": float, "current_value": float, "distance_pct": float},
            "support_line": {"slope": float, "current_value": float, "distance_pct": float},
            "breakout": "bullish_breakout" | "bearish_breakout" | "none"
        }
    """
    if len(df) < 20:
        return {}
    
    # CRIT-2 修复: 使用副本，不污染原始 DataFrame
    _df = df.copy()
        
    # CRIT-1 修复: 真正的局部极值识别 (逐K线对比前后 window 根)
    window = 3
    high_vals = _df['high'].values
    low_vals = _df['low'].values
    n = len(_df)
    
    pivot_high_indices = []
    pivot_low_indices = []
    
    for i in range(window, n - window):
        # Pivot High: 当前 high 严格大于前后 window 根的 high
        is_pivot_high = True
        for j in range(1, window + 1):
            if high_vals[i] <= high_vals[i - j] or high_vals[i] <= high_vals[i + j]:
                is_pivot_high = False
                break
        if is_pivot_high:
            pivot_high_indices.append(i)
        
        # Pivot Low: 当前 low 严格小于前后 window 根的 low
        is_pivot_low = True
        for j in range(1, window + 1):
            if low_vals[i] >= low_vals[i - j] or low_vals[i] >= low_vals[i + j]:
                is_pivot_low = False
                break
        if is_pivot_low:
            pivot_low_indices.append(i)
    
    result = {}
    current_idx = n - 1
    current_price = float(_df['close'].iloc[-1])
    
    # 拟合阻力线 (使用最近的两个高点)
    if len(pivot_high_indices) >= 2:
        x1_h = pivot_high_indices[-2]
        x2_h = pivot_high_indices[-1]
        y1_h = float(high_vals[x1_h])
        y2_h = float(high_vals[x2_h])
        
        if x2_h != x1_h:
            res_slope = (y2_h - y1_h) / (x2_h - x1_h)
            res_val = y2_h + res_slope * (current_idx - x2_h)
            # MED-6 修复: distance_pct 使用绝对值百分比，并标记方向
            dist = (current_price - res_val) / res_val * 100
            result["resistance_line"] = {
                "slope": float(res_slope),
                "current_value": float(res_val),
                "distance_pct": float(f"{abs(dist):.2f}"),
                "above": current_price > res_val
            }
            
    # 拟合支撑线 (使用最近的两个低点)
    if len(pivot_low_indices) >= 2:
        x1_l = pivot_low_indices[-2]
        x2_l = pivot_low_indices[-1]
        y1_l = float(low_vals[x1_l])
        y2_l = float(low_vals[x2_l])
        
        if x2_l != x1_l:
            sup_slope = (y2_l - y1_l) / (x2_l - x1_l)
            sup_val = y2_l + sup_slope * (current_idx - x2_l)
            dist = (current_price - sup_val) / sup_val * 100
            result["support_line"] = {
                "slope": float(sup_slope),
                "current_value": float(sup_val),
                "distance_pct": float(f"{abs(dist):.2f}"),
                "above": current_price > sup_val
            }
            
    # 判断突破
    breakout = "none"
    if "resistance_line" in result and current_price > result["resistance_line"]["current_value"]:
        breakout = "bullish_breakout"
    elif "support_line" in result and current_price < result["support_line"]["current_value"]:
        breakout = "bearish_breakout"
        
    result["breakout"] = breakout
    return result


def _calculate_vpvr(df: pd.DataFrame, bins: int = 40) -> dict:
    """
    计算成交分布图 (Volume Profile Visible Range)
    用于识别成交密集区(HVN)和真空区(LVN)
    """
    try:
        if len(df) < 5:
            return {"hvn": None, "lvn": None}
            
        low = df['low'].min()
        high = df['high'].max()
        if high == low:
            return {"hvn": None, "lvn": None}
            
        # 建立价格分箱
        price_bins = np.linspace(low, high, bins + 1)
        volume_profile = np.zeros(bins)
        
        for _, row in df.iterrows():
            # 简单模型：成交量均匀分布在K线高低点之间
            hl_diff = row['high'] - row['low']
            if hl_diff == 0:
                # 给所在分箱加成交量
                mask = (price_bins[:-1] <= row['high']) & (price_bins[1:] >= row['low'])
            else:
                mask = (price_bins[:-1] <= row['high']) & (price_bins[1:] >= row['low'])
            
            if mask.any():
                volume_profile[mask] += row['volume'] / mask.sum()
        
        # 寻找 HVN (POC)
        max_idx = np.argmax(volume_profile)
        hvn = (price_bins[max_idx] + price_bins[max_idx + 1]) / 2
        
        # 寻找 LVN (真空区 - 在现价附近的最小成交量区)
        current_price = df['close'].iloc[-1]
        # 只在当前价上下 5% 范围内寻找真空区
        nearby_mask = (price_bins[:-1] >= current_price * 0.95) & (price_bins[1:] <= current_price * 1.05)
        if nearby_mask.any():
            nearby_vols = volume_profile[nearby_mask]
            min_idx_in_mask = np.argmin(nearby_vols)
            actual_idx = np.where(nearby_mask)[0][min_idx_in_mask]
            lvn = (price_bins[actual_idx] + price_bins[actual_idx + 1]) / 2
        else:
            min_idx = np.argmin(volume_profile)
            lvn = (price_bins[min_idx] + price_bins[min_idx + 1]) / 2
            
        return {"hvn": float(hvn), "lvn": float(lvn)}
    except Exception as e:
        logger.debug(f"VPVR 计算失败: {e}")
        return {"hvn": None, "lvn": None}


def _detect_smc_indicators(df: pd.DataFrame) -> dict:
    """
    识别 SMC (Smart Money Concepts) 指标: Order Blocks and FVG
    """
    obs = []
    fvgs = []
    
    try:
        if len(df) < 10:
            return {"order_blocks": [], "fvg_gaps": []}
            
        # 1. 识别 FVG (Fair Value Gap)
        for i in range(2, len(df)):
            k1 = df.iloc[i-2]
            k3 = df.iloc[i]
            
            # 看涨 FVG
            if k3['low'] > k1['high']:
                fvgs.append({
                    "type": "bullish",
                    "top": float(k3['low']),
                    "bottom": float(k1['high']),
                    "size_pct": float((k3['low'] - k1['high']) / k1['high'] * 100)
                })
            # 看跌 FVG
            elif k3['high'] < k1['low']:
                fvgs.append({
                    "type": "bearish",
                    "top": float(k1['low']),
                    "bottom": float(k3['high']),
                    "size_pct": float((k1['low'] - k3['high']) / k1['low'] * 100)
                })
        
        # 2. 识别 Order Blocks (OB)
        # 看涨 OB：引发强力拉升前的一根阴线
        for i in range(1, len(df)-2):
            k_prev = df.iloc[i]
            k_next = df.iloc[i+1]
            
            body_size = abs(k_next['close'] - k_next['open'])
            avg_body = df['close'].diff().abs().rolling(10).mean().iloc[i+1]
            if np.isnan(avg_body): avg_body = body_size
            
            if k_next['close'] > k_next['open'] and body_size > avg_body * 1.5:
                if k_prev['close'] < k_prev['open']:
                    obs.append({
                        "type": "bullish",
                        "top": float(k_prev['high']),
                        "bottom": float(k_prev['low']),
                        "symbol": "OB+"
                    })
            
            if k_next['close'] < k_next['open'] and body_size > avg_body * 1.5:
                if k_prev['close'] > k_prev['open']:
                    obs.append({
                        "type": "bearish",
                        "top": float(k_prev['high']),
                        "bottom": float(k_prev['low']),
                        "symbol": "OB-"
                    })
                    
        return {
            "order_blocks": obs[-3:], 
            "fvg_gaps": fvgs[-3:]
        }
    except Exception as e:
        logger.debug(f"SMC 识别失败: {e}")
        return {"order_blocks": [], "fvg_gaps": []}


def _analyze_whale_activity(trades: list[dict], current_price: float) -> dict:
    """
    分析巨鲸活动 (High-Precision)
    
    Args:
        trades: aggTrades 列表
        
    Returns:
        dict: {
            "whale_ratio": 0.45,       # 大单成交占比
            "net_whale_vol": 150000,   # 大单净买入量 (USD)
            "instant_cvd_trend": "up"  # 瞬时CVD趋势
        }
    """
    if not trades:
        return {}
        
    whale_threshold = 50000.0 # $50k 以上定义为大单
    
    total_vol = 0.0
    whale_vol = 0.0
    net_whale_vol = 0.0 # 买入 - 卖出
    buy_vol = 0.0
    sell_vol = 0.0
    
    # 简单的CVD计算 (时间正序: 旧 -> 新)
    # 假设 trades 是按 ID 排序的 (API通常如此)
    
    for t in trades:
        price = float(t['p'])
        qty = float(t['q'])
        is_buyer_maker = t['m'] # True=卖单主动, False=买单主动
        
        value = price * qty
        total_vol += value
        
        # 判定方向
        # is_buyer_maker = True -> 卖方挂单成交 -> 买方是Taker (主动买) wait no
        # Binance API: isBuyerMaker = True means the trade was a SELL (taker was seller)
        # isBuyerMaker = False means the trade was a BUY (taker was buyer)
        
        is_buy = not is_buyer_maker
        
        if is_buy:
            buy_vol += value
        else:
            sell_vol += value
            
        # 巨鲸统计
        if value >= whale_threshold:
            whale_vol += value
            if is_buy:
                net_whale_vol += value
            else:
                net_whale_vol -= value
                
    whale_ratio = whale_vol / total_vol if total_vol > 0 else 0
    
    return {
        "whale_ratio": float(f"{whale_ratio:.2f}"),
        "net_whale_vol": float(f"{net_whale_vol:.2f}"),
        "total_volume_usd": float(f"{total_vol:.2f}"),
        "buy_sell_ratio": float(f"{buy_vol/sell_vol:.2f}") if sell_vol > 0 else 1.0
    }


def _detect_liquidity_gaps(depth: dict) -> list[str]:
    """检测订单簿真空区 (简化版)"""
    gaps = []
    # 如果没有深度数据，返回空
    if not depth or "nearby_ask_1pct" not in depth:
        return gaps
        
    # 逻辑: 如果 Ask 侧 1% 范围内的挂单量极低 (< Bid 侧的 1/5)，则认为上方有真空区
    bid_vol = depth.get("nearby_bid_1pct", 0)
    ask_vol = depth.get("nearby_ask_1pct", 1) # avoid div by zero
    
    if ask_vol > 0 and bid_vol / ask_vol > 5.0:
        gaps.append("upward_liquidity_gap") # 上方无阻力，易拉升
    elif bid_vol > 0 and ask_vol / bid_vol > 5.0:
        gaps.append("downward_liquidity_gap") # 下方无支撑，易砸盘
        
    return gaps
    
    
def _calculate_volatility_score(
    indicators: TechnicalIndicators,
    funding_rate: float,
    whale_data: dict,
    gaps: list
) -> float:
    """
    计算机构级大行情风险指数 (0-100)
    
    Score > 70: 极度危险/变盘在即
    """
    score = 0.0
    
    # 1. 布林带收口 (最强信号)
    # 假设 BB Width < 0.05 (5%) 视为收口
    if indicators.bb_width < 0.05:
        score += 30
    elif indicators.bb_width < 0.10:
        score += 15
        
    # 2. 资金费率异常
    if funding_rate and funding_rate < -0.0005: # -0.05%
        score += 20 # 强轧空风险
    elif funding_rate and abs(funding_rate) > 0.0005:
        score += 10
        
    # 3. 巨鲸异动
    if whale_data:
        whale_ratio = whale_data.get("whale_ratio", 0)
        net_usd = abs(whale_data.get("net_whale_vol", 0))
        if whale_ratio > 0.4: # 大单占比 > 40%
            score += 25
        if net_usd > 1000000: # 净流量 > $1M
            score += 10
            
    # 4. 流动性真空
    if gaps:
        score += 25
        
    # 5. 市场基础活跃分 (Market Sizzle) - 防止绝对 0
    # 即使没有任何风险预警，市场本身的宽窄也代表了基础律动
    if score < 50: # 只在分数较低时补充基础分
        if indicators.bb_width > 0.10: # 宽口，健康波动
            score = max(score, 5.0)
        elif indicators.bb_width > 0.05: # 中等宽度
            score = max(score, 12.0)
        elif indicators.bb_width > 0.02: # 窄口但活跃
            score = max(score, 8.0)
            
    return min(100.0, score)



def _calculate_pivot_points(df: pd.DataFrame) -> dict:
    """
    计算 Pivot Points (Classic & Fibonacci)
    
    基于上一根完整的K线计算。
    """
    if len(df) < 2:
        return {}
        
    # 取上一根已收盘的K线 (当前K线是 iloc[-1] 且未收盘，所以用 iloc[-2])
    # 注意：binance API返回的最后一根K线是当前未完成的。
    prev = df.iloc[-2]
    
    high = prev['high']
    low = prev['low']
    close = prev['close']
    
    # Classic Pivot
    pp = (high + low + close) / 3
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)
    
    # Fibonacci Pivot
    fib_pp = (high + low + close) / 3
    range_val = high - low
    fib_r1 = fib_pp + (0.382 * range_val)
    fib_s1 = fib_pp - (0.382 * range_val)
    fib_r2 = fib_pp + (0.618 * range_val)
    fib_s2 = fib_pp - (0.618 * range_val)
    fib_r3 = fib_pp + (1.0 * range_val)
    fib_s3 = fib_pp - (1.0 * range_val)
    
    return {
        "classic": {
            "p": float(f"{pp:.2f}"),
            "r1": float(f"{r1:.2f}"), "r2": float(f"{r2:.2f}"), "r3": float(f"{r3:.2f}"),
            "s1": float(f"{s1:.2f}"), "s2": float(f"{s2:.2f}"), "s3": float(f"{s3:.2f}")
        },
        "fibonacci": {
            "p": float(f"{fib_pp:.2f}"),
            "r1": float(f"{fib_r1:.2f}"), "r2": float(f"{fib_r2:.2f}"), "r3": float(f"{fib_r3:.2f}"),
            "s1": float(f"{fib_s1:.2f}"), "s2": float(f"{fib_s2:.2f}"), "s3": float(f"{fib_s3:.2f}")
        }
    }


def _calculate_swing_levels(df: pd.DataFrame, window: int = 20) -> dict:
    """
    识别近期波段高低点 (Swing High/Low)
    
    Returns:
        dict: {
            "recent_high": float,
            "recent_low": float,
            "swing_highs": [float], # 最近3个高点
            "swing_lows": [float]   # 最近3个低点
        }
    """
    if len(df) < window:
        return {}
        
    # 截取最近 window 根K线 (排除当前未走完的)
    recent_df = df.iloc[-(window+1):-1]
    
    recent_high = recent_df['high'].max()
    recent_low = recent_df['low'].min()
    
    return {
        "window": window,
        "recent_high": float(f"{recent_high:.2f}"),
        "recent_low": float(f"{recent_low:.2f}")
    }




def _detect_candlestick_patterns(df: pd.DataFrame) -> list[str]:
    """
    识别K线形态
    
    Returns:
        list[str]: 识别到的形态列表
    """
    patterns = []
    if len(df) < 3:
        return patterns
    
    # 最近3根K线
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    
    # 计算蜡烛属性
    body_3 = abs(c3['close'] - c3['open'])
    upper_shadow_3 = c3['high'] - max(c3['close'], c3['open'])
    lower_shadow_3 = min(c3['close'], c3['open']) - c3['low']
    is_bullish_3 = c3['close'] > c3['open']
    is_bearish_3 = c3['close'] < c3['open']
    
    body_2 = abs(c2['close'] - c2['open'])
    is_bullish_2 = c2['close'] > c2['open']
    is_bearish_2 = c2['close'] < c2['open']
    
    # 1. 锤子线 (Hammer) - 下影线长,上影线短,实体小
    if lower_shadow_3 > body_3 * 2 and upper_shadow_3 < body_3 * 0.5:
        patterns.append("锤子线(反转信号)")
    
    # 2. 倒锤子 / 上吊线 (Inverted Hammer / Hanging Man)
    if upper_shadow_3 > body_3 * 2 and lower_shadow_3 < body_3 * 0.5:
        if is_bullish_3:
            patterns.append("倒锤子(潜在反转)")
        else:
            patterns.append("上吊线(见顶信号)")
    
    # 3. 十字星 (Doji)
    avg_body = df['close'].iloc[-10:].std() * 0.3 if len(df) >= 10 else body_3
    if body_3 < avg_body and (upper_shadow_3 > body_3 or lower_shadow_3 > body_3):
        patterns.append("十字星(犹豫信号)")
    
    # 4. 看涨吞没 (Bullish Engulfing)
    if is_bearish_2 and is_bullish_3:
        if c3['open'] < c2['close'] and c3['close'] > c2['open']:
            patterns.append("看涨吞没(强反转)")
    
    # 5. 看跌吞没 (Bearish Engulfing)
    if is_bullish_2 and is_bearish_3:
        if c3['open'] > c2['close'] and c3['close'] < c2['open']:
            patterns.append("看跌吞没(强反转)")
    
    # 6. 早晨之星 (Morning Star) - 三根K线形态
    if len(df) >= 3:
        is_bearish_1 = c1['close'] < c1['open']
        body_1 = abs(c1['close'] - c1['open'])
        if is_bearish_1 and body_2 < body_1 * 0.3 and is_bullish_3 and c3['close'] > (c1['open'] + c1['close']) / 2:
            patterns.append("早晨之星(强反转)")
    
    # 7. 黄昏之星 (Evening Star)
    if len(df) >= 3:
        is_bullish_1 = c1['close'] > c1['open']
        body_1 = abs(c1['close'] - c1['open'])
        if is_bullish_1 and body_2 < body_1 * 0.3 and is_bearish_3 and c3['close'] < (c1['open'] + c1['close']) / 2:
            patterns.append("黄昏之星(见顶信号)")
    
    return patterns


def _detect_signal_conflicts(
    rsi: float, macd_histogram: float, trend_status: str,
    ema_cross_status: str, current_price: float,
    bb_upper: float, bb_lower: float
) -> list[str]:
    """
    检测指标信号冲突
    
    Returns:
        list[str]: 冲突描述列表
    """
    conflicts = []
    
    # 1. RSI 与趋势冲突
    if rsi > 70 and trend_status == "bullish":
        conflicts.append("RSI超买但趋势仍看涨,警惕回调")
    elif rsi < 30 and trend_status == "bearish":
        conflicts.append("RSI超卖但趋势仍看跌,反弹概率增加")
    
    # 2. MACD 与 EMA 冲突
    if macd_histogram > 0 and "空头" in ema_cross_status:
        conflicts.append("MACD多头动能 vs EMA空头排列,方向待确认")
    elif macd_histogram < 0 and "多头" in ema_cross_status:
        conflicts.append("MACD空头动能 vs EMA多头排列,方向待确认")
    
    # 3. 价格与布林带位置
    if current_price > bb_upper and trend_status == "bullish":
        conflicts.append("价格突破布林带上轨,可能超涨")
    elif current_price < bb_lower and trend_status == "bearish":
        conflicts.append("价格跌破布林带下轨,可能超跌")
    
    return conflicts


# ============================================================
# 新闻模拟
# ============================================================

def get_market_sentiment(funding_rate: Optional[float], ls_ratio: Optional[float], rsi: float) -> str:
    """
    基于真实数据计算市场情绪
    """
    sentiments = []
    
    # 1. 资金费率判断
    if funding_rate is not None:
        fr_val = funding_rate * 100
        if fr_val > 0.05:
            sentiments.append(f"资金费率极高({fr_val:.3f}%),多头拥挤")
        elif fr_val > 0.01:
            sentiments.append(f"资金费率偏多({fr_val:.3f}%)")
        elif fr_val < -0.05:
            sentiments.append(f"资金费率极低({fr_val:.3f}%),空头拥挤")
        elif fr_val < 0:
            sentiments.append(f"资金费率偏空({fr_val:.3f}%)")
        else:
            sentiments.append("资金费率中性")
            
    # 2. 多空比判断
    if ls_ratio is not None:
        if ls_ratio > 2.0:
            sentiments.append(f"散户做多情绪极高(L/S {ls_ratio:.2f})")
        elif ls_ratio > 1.2:
            sentiments.append(f"做多情绪占优(L/S {ls_ratio:.2f})")
        elif ls_ratio < 0.5:
            sentiments.append(f"做空情绪极高(L/S {ls_ratio:.2f})")
        elif ls_ratio < 0.8:
            sentiments.append(f"做空情绪占优(L/S {ls_ratio:.2f})")
            
    # 3. RSI辅助
    if rsi > 70:
        sentiments.append("RSI超买")
    elif rsi < 30:
        sentiments.append("RSI超卖")
        
    if not sentiments:
        return "市场情绪数据不足"
        
    return "；".join(sentiments)


# ============================================================
# 辅助工具
# ============================================================

def normalize_symbol(symbol: str) -> str:
    """
    归一化交易对符号
    
    规则:
    1. 转换为大写
    2. 移除分隔符 (-, /, _, .)
    3. 特殊处理: PEPE -> 1000PEPEUSDT, SHIB -> 1000SHIBUSDT, LUNC -> 1000LUNCUSDT
    4. 确保以 USDT 结尾
    """
    if not symbol:
        return ""
    
    # 转换为大写并移除分隔符
    s = symbol.upper()
    s = re.sub(r'[-/_.]', '', s)
    
    # 处理特殊币种 (币安合约通常要求 1000 倍率)
    special_map = {
        "PEPE": "1000PEPE", "SHIB": "1000SHIB", "LUNC": "1000LUNC",
        "XEC": "1000XEC", "FLOKI": "1000FLOKI", "BONK": "1000BONK",
        "RATS": "1000RATS", "SATS": "1000SATS"
    }
    
    # 提取基础代币名称进行检查 (移除 USDT 和可能存在的 1000)
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
# 核心聚合函数
# ============================================================

async def prepare_context_for_ai(
    symbol: str,
    timeframe: str = "4h",
    api_key: str = "",
    api_secret: str = ""
) -> MarketContext:
    '''
    Prepare AI context (Async).
    '''
    # 符号归一化
    symbol = normalize_symbol(symbol)
    
    logger.info(f"开始聚合 {symbol} 市场数据 ({timeframe})...")
    
    # 初始化数据获取器
    fetcher = BinanceDataFetcher(api_key, api_secret)
    
    # 确定趋势周期
    trend_timeframe = "1d"
    if timeframe == "1d" or timeframe == "1w":
        trend_timeframe = "1w"
    elif timeframe == "15m" or timeframe == "1h":
        trend_timeframe = "4h"
    
    
    # 执行所有请求
    import aiohttp
    shared_http_session = aiohttp.ClientSession()
    
    try:
        # 显式启动 Session 以供并发任务复用连接
        await fetcher.start_session()
        
        # 并行获取数据任务
        # 1. 主周期K线 (300根以支持更长AI上下文)
        main_kline_task = fetcher.get_klines(symbol, interval=timeframe, limit=300)
        # 2. 趋势周期K线
        trend_kline_task = fetcher.get_klines(symbol, interval=trend_timeframe, limit=300)
        # 3. 基础数据
        funding_task = fetcher.get_funding_rate(symbol)
        open_interest_task = fetcher.get_open_interest(symbol)
        ls_ratio_task = fetcher.get_long_short_ratio(symbol)
        # 4. 订单簿
        order_book_task = fetcher.get_order_book(symbol)
        # 5. [新] 逐笔成交 (Whale Data)
        trades_task = fetcher.get_agg_trades(symbol, limit=1000)

        # P3 优化: BTC 上下文获取加入并行任务组（山寨币时复用已有 fetcher）
        is_altcoin = symbol not in ("BTCUSDT", "BTCUSD")
        btc_kline_task = fetcher.get_klines("BTCUSDT", interval="4h", limit=30) if is_altcoin else None

        # 组装任务列表
        tasks = [
            main_kline_task,                 # 0
            trend_kline_task,                # 1
            funding_task,                    # 2
            open_interest_task,              # 3
            ls_ratio_task,                   # 4
            order_book_task,                 # 5
            trades_task,                     # 6 [New]
            get_fear_greed_index(shared_http_session),  # 7
            get_crypto_news(symbol, shared_http_session),  # 8 [New: 新闻]
            fetcher.get_funding_rate_history(symbol, limit=24),  # 9 [New: 历史费率]
            fetcher.get_token_fundamentals(symbol),         # 10 [New: 基本面]
        ]
        # P3: 如果是山寨币，将 BTC K线任务追加到并行组
        if btc_kline_task is not None:
            tasks.append(btc_kline_task)     # 10 [P3: BTC 上下文]
        
        # 并发执行并捕获异常 (return_exceptions=True)
        # 并发执行并捕获异常 (return_exceptions=True)
        # IMP-4 Fix: Add explicit timeout for data aggregation
        # Wrap the gathered tasks in wait_for to ensure the whole batch doesn't hang indefinitely
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=20.0 # 20 seconds total timeout for all data
            )
        except asyncio.TimeoutError:
            logger.error(f"Data aggregation timed out for {symbol}")
            # Construct a list of TimeoutErrors to be handled below (mocking results)
            results = [asyncio.TimeoutError("Batch timeout")] * len(tasks)
        
    finally:
        # 确保 Session 关闭
        await fetcher.close_session()
        await shared_http_session.close()
        
    # 解析结果 (容错处理)
    # 1. 核心数据: 主K线 (必须成功)
    df_main = results[0]
    if isinstance(df_main, Exception):
        logger.error(f"核心数据获取失败 (Main Klines): {df_main}")
        import traceback
        logger.error(f"Main Klines Traceback: {traceback.format_tb(df_main.__traceback__)}")
        raise df_main
    
    # 2. 趋势K线 (可选)
    df_trend = results[1]
    if isinstance(df_trend, Exception):
        logger.warning(f"趋势K线获取失败: {df_trend}")
        df_trend = None
        
    # 3. 资金费率 (可选)
    funding_rate = results[2]
    if isinstance(funding_rate, Exception):
        # P5 修复: 使用 None 而非 0.0001，避免偏多默认值误导AI
        logger.debug(f"资金费率获取失败: {funding_rate}")
        funding_rate = None
        
    # 4. 持仓量 (可选)
    open_interest = results[3]
    if isinstance(open_interest, Exception):
        logger.debug(f"持仓量获取失败: {open_interest}")
        open_interest = 0.0
        
    # 5. 多空比 (可选)
    ls_ratio = results[4]
    if isinstance(ls_ratio, Exception):
        # logger.debug(f"多空比获取失败: {ls_ratio}") # debug already logged in func
        ls_ratio = None
        
    # 6. 订单簿 (可选)
    order_book = results[5]
    if isinstance(order_book, Exception):
        logger.debug(f"订单簿获取失败: {order_book}")
        order_book = None  # CRIT-3 修复: 用 None 而非 {}，避免残缺数据

        
    # 8. 逐笔成交 (可选)
    trades = results[6]
    if isinstance(trades, Exception):
        logger.debug(f"逐笔成交获取失败: {trades}")
        trades = []
        
    fear_greed = results[7]
    if isinstance(fear_greed, Exception):
        fear_greed = {"value": 50, "classification": "中性"}

    # 9. 新闻 (可选)
    news_headlines = results[8]
    if isinstance(news_headlines, Exception):
        logger.debug(f"新闻获取失败: {news_headlines}")
        news_headlines = []
    
    # 10. 历史资金费率 (可选)
    funding_history = results[9]
    if isinstance(funding_history, Exception):
        logger.debug(f"历史资金费率获取失败: {funding_history}")
        funding_history = {}

    # 11. 基本面数据 (可选)
    fundamental_data = results[10]
    if isinstance(fundamental_data, Exception):
        logger.debug(f"基本面数据获取失败: {fundamental_data}")
        fundamental_data = None

    
    # 3. 计算技术指标 (CPU密集型,放入线程池)
    loop = asyncio.get_running_loop()
    indicators = await loop.run_in_executor(None, calculate_indicators, df_main)
    
    trend_indicators = None
    trend_kline_summary = ""
    if df_trend is not None and not df_trend.empty:
        trend_indicators = await loop.run_in_executor(None, calculate_indicators, df_trend)
        # 简单构建趋势摘要
        trend_change = (df_trend['close'].iloc[-1] - df_trend['open'].iloc[0]) / df_trend['open'].iloc[0] * 100
        trend_kline_summary = f"{trend_timeframe}周期走势: 现价 {df_trend['close'].iloc[-1]:.2f}, 涨跌幅 {trend_change:+.2f}%, 趋势 {trend_indicators.trend_status}, RSI {trend_indicators.rsi_14:.1f}"
    
    # 4. 计算VPVR (筹码分布) - 新增
    vpvr = await loop.run_in_executor(None, _calculate_vpvr, df_main)
    if vpvr and order_book is not None:
        # 将VPVR注入order_book上下文 (作为一种深度数据)
        order_book["vpvr"] = vpvr
    
    # 5. 获取新闻 (真实API)
    news = news_headlines if news_headlines else []
    
    # 5. 获取市场情绪
    sentiment = get_market_sentiment(funding_rate, ls_ratio, indicators.rsi_14)
    
    # 6. 构建K线摘要
    current_price = df_main['close'].iloc[-1]
    open_price = df_main['open'].iloc[0]
    high_price = df_main['high'].max()
    low_price = df_main['low'].min()
    price_change = (current_price - open_price) / open_price * 100
    
    # 识别K线形态
    last_candle = df_main.iloc[-1]
    body = abs(last_candle['close'] - last_candle['open'])
    upper_shadow = last_candle['high'] - max(last_candle['close'], last_candle['open'])
    lower_shadow = min(last_candle['close'], last_candle['open']) - last_candle['low']
    
    pattern = ""
    if lower_shadow > body * 2 and upper_shadow < body * 0.5:
        pattern = ",最近K线形成锤子线形态(潜在反转信号)"
    elif upper_shadow > body * 2 and lower_shadow < body * 0.5:
        pattern = ",最近K线形成上吊线形态(潜在见顶信号)"
    elif df_main['close'].iloc[-1] > df_main['open'].iloc[-2] and df_main['open'].iloc[-1] < df_main['close'].iloc[-2]:
        if df_main['close'].iloc[-2] < df_main['open'].iloc[-2]:  # 前一根是阴线
            pattern = ",形成看涨吞没形态"
    
    kline_summary = f"""
K-line Summary ({len(df_main)} candles, {timeframe}):
- Open: {open_price:.2f} USDT
- High: {high_price:.2f} USDT
- Low: {low_price:.2f} USDT
- Close: {current_price:.2f} USDT
- Change: {price_change:+.2f}%
- Trend: {indicators.trend_status}{pattern}
- Volume: {"Increasing" if df_main['volume'].iloc[-5:].mean() > df_main['volume'].iloc[-20:-5].mean() else "Decreasing"}
""".strip()
    
    # 构建上下文对象
    # 确保没有NaN值 (JSON序列化会失败)
    df_main_clean = df_main.fillna(0.0)
    
    # Calculate advanced metrics
    whale_data = _analyze_whale_activity(trades, current_price)
    gaps = _detect_liquidity_gaps(order_book)
    
    # 2. 计算 Pivot Points
    pivot_points = _calculate_pivot_points(df_main)
    
    # 3. 计算 Swing Levels
    swing_levels = _calculate_swing_levels(df_main)

    # P3 优化: 从并行结果中解析 BTC 上下文（不再单独创建 fetcher）
    btc_context = None
    if is_altcoin and len(results) > 11:
        btc_klines_result = results[11]
        if not isinstance(btc_klines_result, Exception) and btc_klines_result is not None and not btc_klines_result.empty:
            try:
                btc_klines = btc_klines_result
                btc_price = btc_klines['close'].iloc[-1]
                btc_change = (btc_klines['close'].iloc[-1] - btc_klines['open'].iloc[0]) / btc_klines['open'].iloc[0] * 100
                btc_close = btc_klines['close']
                btc_sma20 = btc_close.rolling(20).mean().iloc[-1] if len(btc_close) >= 20 else btc_price
                btc_trend = "bullish" if btc_price > btc_sma20 else "bearish"
                # 简化 RSI
                btc_delta = btc_close.diff()
                btc_gain = btc_delta.where(btc_delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
                btc_loss = (-btc_delta.where(btc_delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
                btc_rsi = 50.0
                if btc_loss.iloc[-1] != 0:
                    btc_rs = btc_gain.iloc[-1] / btc_loss.iloc[-1]
                    btc_rsi = 100 - (100 / (1 + btc_rs))
                btc_context = {
                    "price": _safe_float(btc_price),
                    "change_pct": round(btc_change, 2),
                    "trend": btc_trend,
                    "rsi": round(_safe_float(btc_rsi, 50.0), 1)
                }
                logger.info(f"BTC 上下文注入: 价格={btc_price:.2f}, 趋势={btc_trend}, RSI={btc_rsi:.1f}")
            except Exception as e:
                logger.debug(f"BTC 上下文解析失败 (非关键): {e}")
        else:
            if isinstance(btc_klines_result, Exception):
                logger.debug(f"BTC K线获取失败 (非关键): {btc_klines_result}")
    else:
        btc_context = None

    context = MarketContext(
        symbol=symbol,
        current_price=_safe_float(current_price),
        kline_summary=kline_summary,
        klines=df_main_clean.assign(timestamp=df_main_clean['timestamp'].astype('int64') // 10**6).to_dict('records'),
        indicators=indicators,
        funding_rate=_safe_float(funding_rate) if funding_rate is not None else None,
        open_interest=_safe_float(open_interest) if open_interest is not None else None,
        # 机构数据
        whale_activity=whale_data,
        liquidity_gaps=gaps,
        volatility_score=_calculate_volatility_score(
            indicators, funding_rate or 0, whale_data, gaps
        ),
        # TA S/R
        pivot_points=pivot_points,
        swing_levels=swing_levels,
        # 新闻 + 情绪
        news_headlines=news,
        market_sentiment=sentiment,
        timeframe=timeframe,
        order_book=order_book,
        trend_kline_summary=trend_kline_summary,
        trend_klines=df_trend.assign(timestamp=df_trend['timestamp'].astype('int64') // 10**6).to_dict('records') if df_trend is not None and not df_trend.empty else None,
        trend_indicators=trend_indicators,
        fear_greed_index=fear_greed,
        # 新增数据源
        long_short_ratio=ls_ratio,
        funding_rate_history=funding_history if funding_history else None,
        fundamental_data=fundamental_data,
        btc_context=btc_context,
        volume_ratio=_safe_float(indicators.volume_ratio),
    )
    
    logger.info(f"{symbol} 市场上下文聚合完成")
    
    return context


def format_context_as_text(context: MarketContext) -> str:
    # Format context as text summary
    # Used for logging or simple display
    lines = [
        f"{'='*50}",
        f"📊 {context.symbol} Market Analysis Context",
        f"{'='*50}",
        "",
        "[K-line Trend]",
        context.kline_summary,
        "",
        "[Technical Indicators]",
        f"  RSI(14): {context.indicators.rsi_14:.2f}",
        f"  MACD: {context.indicators.macd_line:.4f} / Signal: {context.indicators.macd_signal:.4f}",
        f"  MA20: {context.indicators.sma_20:.2f} | MA50: {context.indicators.sma_50:.2f}",
        f"  Bollinger: {context.indicators.bb_lower:.2f} ~ {context.indicators.bb_upper:.2f}",
        f"  ATR(14): {context.indicators.atr_14:.2f}",
        f"  Trend: {context.indicators.trend_status} | MA Cross: {context.indicators.ma_cross_status}",
        "",
        "[Funding Data]",
        f"  Funding Rate: {context.funding_rate*100:.4f}%" if context.funding_rate else "  Funding Rate: N/A",
        f"  Open Interest: {context.open_interest:,.0f}" if context.open_interest else "  Open Interest: N/A",
        "",
        "[Market Sentiment]",
        f"  {context.market_sentiment}",
        "",
        "[Related News]",
    ]
    
    for i, headline in enumerate(context.news_headlines, 1):
        lines.append(f"  {i}. {headline}")
    
    if not context.news_headlines:
         lines.append("  (No major news)")
    
    lines.append(f"{'='*50}")
    
    return "\n".join(lines)


def _convert_to_python_types(data):
    """递归将 numpy 类型转换为 python 原生类型，并处理 NaN/Inf"""
    import numpy as np
    import math
    if isinstance(data, dict):
        return {k: _convert_to_python_types(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_to_python_types(v) for v in data]
    elif isinstance(data, (np.int64, np.int32, np.int16, np.int8, np.uint64, np.uint32, np.uint16, np.uint8)):
        return int(data)
    elif isinstance(data, (np.float64, np.float32, np.float16)):
        val = float(data)
        return 0.0 if math.isnan(val) or math.isinf(val) else val
    elif isinstance(data, (np.bool_, bool)):
        return bool(data)
    elif isinstance(data, np.ndarray):
        return _convert_to_python_types(data.tolist())
    elif isinstance(data, float):
        return 0.0 if math.isnan(data) or math.isinf(data) else data
    return data


async def get_war_room_dashboard(symbol: str = "BTCUSDT") -> dict:
    """
    获取主力战情室 (War Room) 仪表盘数据
    
    聚合 4个核心维度:
    1. 多周期共振 (15m, 1h, 4h, 1d)
    2. 关键位攻防 (Pivot/Swing距离)
    3. 资金面异动 (Whale/CVD/OrderBook)
    4. 波动率预警 (BB Width)
    """
    logger.info(f"正在构建主力战情室数据 ({symbol})...")
    
    # 1. 归一化 Symbol
    symbol = normalize_symbol(symbol)
    
    # 2. 获取全局 Fetcher
    fetcher = await get_global_fetcher()
    if not fetcher:
        return None
        
    try:
        # 3. 并行获取多周期数据
        # 4h 作为主周期用于计算关键位和波动率
        tasks = [
            fetcher.get_klines(symbol, "15m", limit=50),  # 0
            fetcher.get_klines(symbol, "1h", limit=50),   # 1
            fetcher.get_klines(symbol, "4h", limit=100),  # 2 (Main)
            fetcher.get_klines(symbol, "1d", limit=50),   # 3
            fetcher.get_agg_trades(symbol, limit=1000),   # 4 (Whale)
            fetcher.get_order_book(symbol),               # 5 (Depth)
            fetcher.get_funding_rate(symbol),             # 6
            fetcher.get_long_short_ratio(symbol),         # 7
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. 解析结果
        k_15m = results[0] if not isinstance(results[0], Exception) else None
        k_1h = results[1] if not isinstance(results[1], Exception) else None
        k_4h = results[2] if not isinstance(results[2], Exception) else None
        k_1d = results[3] if not isinstance(results[3], Exception) else None
        
        trades = results[4] if not isinstance(results[4], Exception) else []
        order_book = results[5] if not isinstance(results[5], Exception) else None
        funding = results[6] if not isinstance(results[6], Exception) else None
        ls_ratio = results[7] if not isinstance(results[7], Exception) else None
        
        if k_4h is None or k_4h.empty:
            logger.error("战情室核心数据获取失败 (4h Klines)")
            return None
            
        # 5. 计算技术指标 (多周期)
        loop = asyncio.get_running_loop()
        
        # 定义轻量级计算任务
        async def calc_trend(df):
            if df is None or df.empty: return None
            return await loop.run_in_executor(None, calculate_indicators, df)
            
        t_15m, t_1h, t_4h, t_1d = await asyncio.gather(
            calc_trend(k_15m),
            calc_trend(k_1h),
            calc_trend(k_4h),
            calc_trend(k_1d)
        )
        
        current_price = k_4h['close'].iloc[-1]
        
        # 6. 构建模块数据
        
        # [Module 1] 多周期共振
        trend_resonance = []
        timelines = [("15m", t_15m), ("1h", t_1h), ("4h", t_4h), ("1d", t_1d)]
        
        bullish_count = 0
        bearish_count = 0
        
        for tf, ind in timelines:
            if ind:
                status = "neutral"
                if ind.trend_status == "bullish":
                    status = "bullish"
                    bullish_count += 1
                elif ind.trend_status == "bearish":
                    status = "bearish"
                    bearish_count += 1
                    
                trend_resonance.append({
                    "timeframe": tf,
                    "status": status,
                    "rsi": ind.rsi_14,
                    "ma_aligned": ind.ma_cross_status == "金叉" or ind.sma_20 > ind.sma_50
                })
            else:
                trend_resonance.append({"timeframe": tf, "status": "loading"})
                
        resonance_summary = "震荡"
        if bullish_count >= 3: resonance_summary = "多头共振"
        elif bearish_count >= 3: resonance_summary = "空头共振"
        
        # [Module 2] 关键位攻防
        # 使用 4h 数据计算 Pivot 和 Swing
        pivot_points = _calculate_pivot_points(k_4h)
        swing_levels = _calculate_swing_levels(k_4h)
        
        # 寻找最近的支撑和阻力
        supports = []
        resistances = []
        
        # 提取 Pivot Levels
        pivot_cn_map = {
            "p": "轴心核心点", 
            "r1": "第一阻力位 (R1)", "r2": "第二阻力位 (R2)", "r3": "第三阻力位 (R3)",
            "s1": "第一支撑位 (S1)", "s2": "第二支撑位 (S2)", "s3": "第三支撑位 (S3)"
        }
        if "classic" in pivot_points:
            p = pivot_points["classic"]
            for k, v in p.items():
                label = pivot_cn_map.get(k, k)
                if v < current_price: supports.append((label, v))
                elif v > current_price: resistances.append((label, v))
                
        # 提取 Swing Levels
        if swing_levels:
            if swing_levels.get("recent_low"): supports.append(("波段前低", swing_levels["recent_low"]))
            if swing_levels.get("recent_high"): resistances.append(("波段前高", swing_levels["recent_high"]))
            
        # 排序
        supports.sort(key=lambda x: x[1], reverse=True) # 从高到低 (最近的在前面)
        resistances.sort(key=lambda x: x[1])            # 从低到高 (最近的在前面)
        
        # 默认值处理
        default_support_label = "主要支撑位"
        default_resistance_label = "主要阻力位"
        
        nearest_support = supports[0] if supports else (default_support_label, current_price * 0.9)
        nearest_resistance = resistances[0] if resistances else (default_resistance_label, current_price * 1.1)
        
        safe_current_price = current_price if current_price > 0 else 1.0 # 除零保护
        dist_support = (current_price - nearest_support[1]) / safe_current_price * 100
        dist_resistance = (nearest_resistance[1] - current_price) / safe_current_price * 100
        
        key_levels = {
            "current_price": current_price,
            "nearest_support": {
                "label": nearest_support[0],
                "price": nearest_support[1],
                "distance_pct": round(dist_support, 2)
            },
            "nearest_resistance": {
                "label": nearest_resistance[0],
                "price": nearest_resistance[1],
                "distance_pct": round(dist_resistance, 2)
            },
            "in_sniper_zone": dist_support < 0.5 or dist_resistance < 0.5
        }
        
        # [Module 3] 资金异动 (Smart Money)
        whale_data = _analyze_whale_activity(trades, current_price)
        gaps = _detect_liquidity_gaps(order_book)
        
        # 简单的 CVD 背离检测
        # 如果价格上涨趋势但 CVD (net_whale) 为负 -> 诱多
        # 如果价格下跌趋势但 CVD 为正 -> 吸筹
        sm_signal = "neutral"
        if t_4h:
            # 价格趋势
            price_trend_up = k_4h['close'].iloc[-1] > k_4h['close'].iloc[-5]
            net_whale_buy = whale_data.get("net_whale_vol", 0) > 0
            
            if price_trend_up and not net_whale_buy:
                sm_signal = "bearish_divergence" # 诱多 (价涨量缩/大户出货)
            elif not price_trend_up and net_whale_buy:
                sm_signal = "bullish_accumulation" # 吸筹 (价跌大户买入)
            elif price_trend_up and net_whale_buy:
                sm_signal = "bullish_confirmed" # 量价齐升
            elif not price_trend_up and not net_whale_buy:
                sm_signal = "bearish_confirmed" # 量价齐跌
                
        smart_money = {
            "signal": sm_signal,
            "whale_ratio": whale_data.get("whale_ratio", 0),
            "net_whale_vol": whale_data.get("net_whale_vol", 0),
            "liquidity_gaps": gaps,
            "funding_rate": funding if funding is not None else 0,
            "long_short_ratio": ls_ratio if ls_ratio is not None else 0
        }
        
        # [Module 4] 波动率预警
        vol_score = 0
        bb_width = 0
        if t_4h:
            bb_width = t_4h.bb_width
            vol_score = _calculate_volatility_score(t_4h, funding, whale_data, gaps)
            
        volatility = {
            "score": vol_score,
            "bb_width": bb_width,
            "status": "storm_alert" if bb_width < 0.05 or vol_score > 70 else "calm"
        }
        
        # [Module 5] 战情指南 (Final Verdict)
        # 根据以上四个模块的数据，生成一条针对当前行情的“大白话”实战结论
        verdict = ""
        risk_score = 0 # 0-100倾向
        
        # 1. 检测共振方向
        if resonance_summary == "多头共振":
            verdict = "四周期多头共振，大势向好。"
            risk_score += 20
        elif resonance_summary == "空头共振":
            verdict = "四周期空头共振，空方占优。"
            risk_score -= 20
        else:
            verdict = "多空陷入拉锯，观望为主。"

        # 2. 结合主力资金
        if smart_money["signal"] == "bullish_accumulation":
            verdict += "主力大单正在吸筹，关注低吸机会。"
            risk_score += 15
        elif smart_money["signal"] == "bearish_divergence":
            verdict += "价格虽稳但主力正在撤离，警惕诱多反杀。"
            risk_score -= 25
        elif smart_money["signal"] == "bearish_confirmed":
            verdict += "量价齐跌且主力加速出货，严禁摸底。"
            risk_score -= 20
        
        # 3. 结合关键位压力
        if key_levels["in_sniper_zone"]:
            if dist_resistance < 0.5:
                verdict += f" 接近{nearest_resistance[0]}，若冲高无量建议止盈或短空。"
                risk_score -= 10
            elif dist_support < 0.5:
                verdict += f" 踩稳{nearest_support[0]}，是极佳的博开多点位。"
                risk_score += 15

        # 4. 结合波动率
        if volatility["status"] == "storm_alert":
            verdict = "⚠️ 极端收敛警告！市场恐有剧烈波动，请即刻收紧止损。"
        
        # 修正结论前缀
        if not verdict: verdict = "市场数据动态生成中，请保持关注。"

        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "trend_resonance": {
                "summary": resonance_summary,
                "details": trend_resonance
            },
            "key_levels": key_levels,
            "smart_money": smart_money,
            "volatility": volatility,
            "verdict": verdict,
            "verdict_score": risk_score
        }
        
        return _convert_to_python_types(result)
        
    except Exception as e:
        logger.error(f"构建战情室数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None



# ============================================================
# 模块测试入口
# ============================================================

if __name__ == "__main__":
    # 测试数据聚合功能
    print("测试数据聚合模块...")
    
    async def main():
        # 测试不同交易对
        for symbol in ["ETHUSDT", "BTCUSDT"]:
            print(f"\n{'='*60}")
            print(f"测试 {symbol}")
            print(f"{'='*60}")
            
            context = await prepare_context_for_ai(symbol)
            
            # 打印格式化结果
            print(format_context_as_text(context))
            
            # 打印字典格式(用于AI)
            print("\n📤 AI上下文字典格式:")
            ai_dict = context.to_dict()
            for key, value in ai_dict.items():
                if isinstance(value, list):
                    print(f"  {key}: {value[:2]}..." if len(value) > 2 else f"  {key}: {value}")
                elif isinstance(value, str) and len(value) > 50:
                    print(f"  {key}: {value[:50]}...")
                else:
                    print(f"  {key}: {value}")

    asyncio.run(main())
