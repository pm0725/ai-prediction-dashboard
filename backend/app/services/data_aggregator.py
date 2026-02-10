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
class TechnicalIndicators:
    """技术指标数据"""
    # 移动平均 (无默认值)
    sma_20: float
    sma_50: float
    ema_12: float
    ema_26: float
    
    # RSI (无默认值)
    rsi_14: float
    
    # MACD (无默认值)
    macd_line: float
    macd_signal: float
    macd_histogram: float
    
    # 布林带 (无默认值)
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_width: float
    
    # 波动率 (无默认值)
    atr_14: float
    
    # 趋势状态 (无默认值)
    trend_status: str  # "bullish", "bearish", "neutral"
    ma_cross_status: str  # "golden_cross", "death_cross", "none"
    
    # ========== 以下为有默认值的字段 ==========
    # 新增: EMA快慢线
    ema_9: float = 0.0
    ema_21: float = 0.0
    ema_cross_status: str = ""  # EMA9/21交叉状态
    
    # K线形态 (新增)
    candlestick_patterns: list = None  # ["锤子线", "看涨吞没"]
    
    # 信号冲突检测 (新增)
    signal_conflicts: list = None  # ["指标冲突1", "指标冲突2"]
    
    # 趋势线 (新增)
    trend_lines: dict = None  # {resistance, support, breakout}
    
    def __post_init__(self):
        if self.candlestick_patterns is None:
            self.candlestick_patterns = []
        if self.signal_conflicts is None:
            self.signal_conflicts = []
        if self.trend_lines is None:
            self.trend_lines = {}


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
    trend_indicators: Optional[TechnicalIndicators] = None # 趋势周期指标
    fear_greed_index: Optional[dict] = None    # 恐惧贪婪指数
    
    # 新增: 机构级预警字段
    volatility_score: float = 0.0              # 0-100 波动率风险分
    whale_activity: Optional[dict] = None      # 巨鲸活动分析
    liquidity_gaps: list = None                # 订单簿真空区
    
    # 新增: 传统技术支撑/阻力 (Traditional TA)
    pivot_points: Optional[dict] = None        # Pivot Points
    swing_levels: Optional[dict] = None        # Swing Highs/Lows

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
            "atr": self.indicators.atr_14,  # 新增: ATR波动率
            "news_headlines": self.news_headlines,
            "market_sentiment": self.market_sentiment,
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
                "candlestick_patterns": self.trend_indicators.candlestick_patterns if self.trend_indicators else []
            }
        
        # 注入恐惧贪婪指数
        if self.fear_greed_index:
            data["fear_greed_index"] = self.fear_greed_index
            
        # 注入理论清算价格
        data["liquidation_levels"] = self._calculate_liquidation_levels()
            
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
        
    try:
        async with session.get(
            "https://api.alternative.me/fng/?limit=1",
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
            logger.info("BinanceDataFetcher 长连接会话已建立")

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
            
        requests_params = {}
        proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        if proxy:
            requests_params['proxies'] = {'http': proxy, 'https': proxy}
        
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
        try:
            # 获取所有ticker,这是一次调用高效获取所有市场数据
            all_tickers = await client.futures_ticker()
            
            # 创建快速查找字典
            ticker_map = {t['symbol']: t for t in all_tickers}
            
            for symbol in symbols:
                if symbol in ticker_map:
                    t = ticker_map[symbol]
                    results.append({
                        "symbol": symbol,
                        "price": float(t['lastPrice']),
                        "change_percent": float(t['priceChangePercent']),
                        "quote_volume": float(t['quoteVolume']) # Added for Volume Spike Detection
                    })
        except Exception as e:
            logger.error(f"获取Ticker失败: {e}")
        finally:
            if client:
                await self._close_temp_client(client)
                
        return results

    async def get_long_short_ratio(self, symbol: str) -> Optional[float]:
        """获取多空持仓人数比"""
        symbol = normalize_symbol(symbol)
        if not BINANCE_AVAILABLE:
            return None
            
        client = await self._get_client()
        try:
            # Top Long/Short Account Ratio (5m)
            # 注意: 此API可能在某些python-binance版本中不可用
            if not hasattr(client, 'futures_top_long_short_account_ratio'):
                logger.debug("python-binance版本不支持futures_top_long_short_account_ratio")
                return None
            info = await client.futures_top_long_short_account_ratio(symbol=symbol, period="5m", limit=1)
            if info:
                return float(info[0]['longShortRatio'])
        except AttributeError:
            logger.debug("多空比API方法不存在,跳过")
        except Exception as e:
            logger.debug(f"获取多空比失败 (非关键): {e}")
        finally:
            if client:
                await self._close_temp_client(client)
        return None

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
        
        # 简化MACD
        macd_line = ema_12 - ema_26
        macd_signal = pd.Series([ema_12 - ema_26]).ewm(span=9).mean().iloc[-1]
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
        trend_lines=trend_lines
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

def _calculate_vpvr(df: pd.DataFrame, bins: int = 50) -> dict:
    """
    计算成交量分布 (VPVR) - 向量化优化版
    """
    if df.empty:
        return {}
        
    # 1. 确定价格范围
    min_price = df['low'].min()
    max_price = df['high'].max()
    if max_price <= min_price:
        return {}
        
    # 2. 向量化分桶 (使用 mid price)
    mid_prices = (df['high'] + df['low']) / 2
    
    # 使用 pd.cut 快速分桶
    # labels=False 返回桶的索引(0-based)
    # right=True (default) -> (a, b], include_lowest=True -> [min, b] for first bin
    try:
        df = df.copy() # Avoid SettingWithCopy warning on input df
        df['bin_idx'] = pd.cut(mid_prices, bins=bins, include_lowest=True, labels=False)
    except Exception as e:
        logger.error(f"VPVR分桶计算失败: {e}")
        return {}
    
    # 3. 聚合计算
    # 按桶索引分组求和 volume
    volume_profile = df.groupby('bin_idx')['volume'].sum()
    
    if volume_profile.empty:
        return {}
        
    # 4. 构建结果列表
    bin_size = (max_price - min_price) / bins
    profile = []
    
    for bin_idx, volume in volume_profile.items():
        # 计算该桶的中心价格
        price_level = min_price + (bin_idx * bin_size) + (bin_size / 2)
        profile.append({"price": price_level, "volume": volume})
    
    profile.sort(key=lambda x: x["price"])
    
    if not profile:
        return {}
        
    # 5. 计算POC (Point of Control)
    poc_node = max(profile, key=lambda x: x["volume"])
    poc = poc_node["price"]
    
    # 6. 计算价值区域 (VAH, VAL) - 70% 成交量
    total_volume = sum(p["volume"] for p in profile)
    target_volume = total_volume * 0.7
    
    poc_idx = next(i for i, p in enumerate(profile) if p["price"] == poc)
    
    current_volume = poc_node["volume"]
    up_idx = poc_idx
    down_idx = poc_idx
    
    while current_volume < target_volume:
        # 尝试向上扩展
        next_up_vol = profile[up_idx + 1]["volume"] if up_idx + 1 < len(profile) else 0
        # 尝试向下扩展
        next_down_vol = profile[down_idx - 1]["volume"] if down_idx - 1 >= 0 else 0
        
        if next_up_vol == 0 and next_down_vol == 0:
            break
            
        # 优先扩展成交量大的一侧 (更符合Auction Market Theory)
        if next_up_vol > next_down_vol:
            up_idx += 1
            current_volume += next_up_vol
        else:
            down_idx -= 1
            current_volume += next_down_vol
            
    val = profile[down_idx]["price"]
    vah = profile[up_idx]["price"]
    
    return {
        "poc": float(f"{poc:.2f}"),
        "vah": float(f"{vah:.2f}"),
        "val": float(f"{val:.2f}")
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
    
    # 并行获取数据任务
    # 1. 主周期K线
    main_kline_task = fetcher.get_klines(symbol, interval=timeframe, limit=50)
    # 2. 趋势周期K线
    trend_kline_task = fetcher.get_klines(symbol, interval=trend_timeframe, limit=50)
    # 3. 基础数据
    funding_task = fetcher.get_funding_rate(symbol)
    open_interest_task = fetcher.get_open_interest(symbol)
    ls_ratio_task = fetcher.get_long_short_ratio(symbol)
    # 4. 订单簿
    order_book_task = fetcher.get_order_book(symbol)
    
    # 5. [新] 逐笔成交 (Whale Data)
    trades_task = fetcher.get_agg_trades(symbol, limit=1000)

    
    # 执行所有请求
    import aiohttp
    shared_http_session = aiohttp.ClientSession()
    
    try:
        # 显式启动 Session 以供并发任务复用连接
        await fetcher.start_session()
        
        # 组装任务列表
        tasks = [
            main_kline_task,                 # 0
            trend_kline_task,                # 1
            funding_task,                    # 2
            open_interest_task,              # 3
            ls_ratio_task,                   # 4
            order_book_task,                 # 5
            trades_task,                     # 6 [New]
            get_fear_greed_index(shared_http_session)  # 7
        ]
        
        # 并发执行并捕获异常 (return_exceptions=True)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
    finally:
        # 确保 Session 关闭
        await fetcher.close_session()
        await shared_http_session.close()
        
    # 解析结果 (容错处理)
    # 1. 核心数据: 主K线 (必须成功)
    df_main = results[0]
    if isinstance(df_main, Exception):
        logger.error(f"核心数据获取失败 (Main Klines): {df_main}")
        raise df_main
    
    # 2. 趋势K线 (可选)
    df_trend = results[1]
    if isinstance(df_trend, Exception):
        logger.warning(f"趋势K线获取失败: {df_trend}")
        df_trend = None
        
    # 3. 资金费率 (可选)
    funding_rate = results[2]
    if isinstance(funding_rate, Exception):
        logger.debug(f"资金费率获取失败: {funding_rate}")
        funding_rate = 0.0001
        
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
        
    fear_greed = results[7] # Index shifted due to insertion
    if isinstance(fear_greed, Exception):
        fear_greed = {"value": 50, "classification": "中性"}

    
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
    
    # 4. 获取新闻 (暂无真实源,返回空)
    news = []
    
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

    context = MarketContext(
        symbol=symbol,
        current_price=_safe_float(current_price),
        kline_summary=kline_summary,
        klines=df_main_clean.assign(timestamp=df_main_clean['timestamp'].astype('int64') // 10**6).to_dict('records'),
        indicators=indicators,
        funding_rate=_safe_float(funding_rate) if funding_rate is not None else None,
        open_interest=_safe_float(open_interest) if open_interest is not None else None,
        # 新增机构数据
        whale_activity=whale_data,
        liquidity_gaps=gaps,
        volatility_score=_calculate_volatility_score(
            indicators, funding_rate or 0, whale_data, gaps
        ),
        # 新增 TA S/R
        pivot_points=pivot_points,
        swing_levels=swing_levels,
        
        news_headlines=news,
        market_sentiment=sentiment,
        timeframe=timeframe,  # 传入分析周期
        order_book=order_book,
        trend_kline_summary=trend_kline_summary,
        trend_indicators=trend_indicators,
        fear_greed_index=fear_greed
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
