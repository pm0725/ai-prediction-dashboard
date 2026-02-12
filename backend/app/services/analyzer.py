"""
智链预测 - 数据分析器模块
=========================
技术指标计算和数据预处理
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import math

from .data_fetcher import Kline, Ticker, FundingRate
from app.models.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


# ============================================================
# 数据模型
# ============================================================




@dataclass
class MarketAnalysis:
    """市场分析结果"""
    symbol: str
    current_price: float
    indicators: TechnicalIndicators
    price_change_24h: float = 0.0
    volume_24h: float = 0.0
    funding_rate: float = 0.0
    market_sentiment: str = "中性"
    key_levels: Dict[str, float] = field(default_factory=dict)
    kline_summary: str = ""
    news_headlines: List[str] = field(default_factory=list)
    analysis_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "indicators": self.indicators.to_dict(),
            "price_change_24h": self.price_change_24h,
            "volume_24h": self.volume_24h,
            "funding_rate": self.funding_rate,
            "market_sentiment": self.market_sentiment,
            "key_levels": self.key_levels,
            "kline_summary": self.kline_summary,
            "news_headlines": self.news_headlines,
            "analysis_time": self.analysis_time
        }


# ============================================================
# 技术指标计算
# ============================================================

class TechnicalAnalyzer:
    """技术分析计算器"""
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> float:
        """计算简单移动平均线"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """计算指数移动平均线"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """计算相对强弱指标"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[float, float, float]:
        """计算MACD"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
        
        ema_fast = TechnicalAnalyzer.calculate_ema(prices, fast)
        ema_slow = TechnicalAnalyzer.calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # 计算信号线（MACD的EMA）
        macd_values = []
        for i in range(slow, len(prices) + 1):
            ef = TechnicalAnalyzer.calculate_ema(prices[:i], fast)
            es = TechnicalAnalyzer.calculate_ema(prices[:i], slow)
            macd_values.append(ef - es)
        
        if len(macd_values) < signal:
            signal_line = macd_line
        else:
            signal_line = TechnicalAnalyzer.calculate_ema(macd_values, signal)
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """计算布林带"""
        if len(prices) < period:
            price = prices[-1] if prices else 0
            return price * 1.02, price, price * 0.98
        
        sma = sum(prices[-period:]) / period
        
        # 计算标准差
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)
        
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        
        return upper, sma, lower
    
    @staticmethod
    def calculate_atr(klines: List[Kline], period: int = 14) -> float:
        """计算平均真实波幅"""
        if len(klines) < 2:
            return 0
        
        true_ranges = []
        for i in range(1, len(klines)):
            high = klines[i].high
            low = klines[i].low
            prev_close = klines[i-1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0
        
        return sum(true_ranges[-period:]) / period
    
    @classmethod
    def analyze(cls, klines: List[Kline]) -> TechnicalIndicators:
        """执行完整技术分析"""
        if not klines:
            return TechnicalIndicators()
        
        # 提取收盘价序列
        closes = [k.close for k in klines]
        current_price = closes[-1]
        
        # 计算移动平均线
        sma_20 = cls.calculate_sma(closes, 20)
        sma_50 = cls.calculate_sma(closes, 50)
        ema_12 = cls.calculate_ema(closes, 12)
        ema_26 = cls.calculate_ema(closes, 26)
        
        # 计算RSI
        rsi = cls.calculate_rsi(closes, 14)
        
        # 计算MACD
        macd_line, macd_signal, macd_hist = cls.calculate_macd(closes)
        
        # 计算布林带
        bb_upper, bb_middle, bb_lower = cls.calculate_bollinger_bands(closes)
        bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0
        
        # 计算ATR
        atr = cls.calculate_atr(klines, 14)
        
        # 判断趋势
        if current_price > sma_20 > sma_50:
            trend = "bullish"
        elif current_price < sma_20 < sma_50:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # 判断均线交叉
        if len(closes) >= 2:
            prev_sma_20 = cls.calculate_sma(closes[:-1], 20)
            prev_sma_50 = cls.calculate_sma(closes[:-1], 50)
            
            if prev_sma_20 < prev_sma_50 and sma_20 > sma_50:
                ma_cross = "金叉形成"
            elif prev_sma_20 > prev_sma_50 and sma_20 < sma_50:
                ma_cross = "死叉形成"
            elif sma_20 > sma_50:
                ma_cross = "多头排列"
            elif sma_20 < sma_50:
                ma_cross = "空头排列"
            else:
                ma_cross = "均线缠绕"
        else:
            ma_cross = "数据不足"
        
        # 判断波动率
        atr_percent = (atr / current_price) * 100 if current_price > 0 else 0
        if atr_percent > 3:
            volatility = "极高"
        elif atr_percent > 2:
            volatility = "高"
        elif atr_percent > 1:
            volatility = "中等"
        else:
            volatility = "低"
        
        return TechnicalIndicators(
            sma_20=sma_20,
            sma_50=sma_50,
            ema_12=ema_12,
            ema_26=ema_26,
            rsi_14=rsi,
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_hist,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            bb_width=bb_width,
            atr_14=atr,
            trend_status=trend,
            ma_cross_status=ma_cross,
            volatility_level=volatility
        )


# ============================================================
# 市场分析器
# ============================================================

class MarketAnalyzer:
    """市场分析器"""
    
    # 模拟新闻数据
    MOCK_NEWS = {
        "BTCUSDT": [
            "贝莱德比特币ETF日均流入突破2亿美元",
            "MicroStrategy再次增持1500枚BTC",
            "比特币挖矿难度创历史新高"
        ],
        "ETHUSDT": [
            "以太坊Layer2总锁仓量突破400亿美元",
            "Vitalik发布以太坊扩容路线图更新",
            "ETH ETF获批预期升温"
        ],
        "SOLUSDT": [
            "Solana DeFi活跃度创新高",
            "知名机构增持SOL头寸",
            "Solana生态NFT交易量激增"
        ],
        "DEFAULT": [
            "加密市场整体情绪偏乐观",
            "机构资金持续流入数字资产",
            "监管政策逐步明朗化"
        ]
    }
    
    def __init__(self):
        self.technical = TechnicalAnalyzer()
    
    def analyze_market(
        self,
        symbol: str,
        klines: List[Kline],
        ticker: Optional[Ticker] = None,
        funding: Optional[FundingRate] = None
    ) -> MarketAnalysis:
        """执行完整市场分析"""
        
        # 计算技术指标
        indicators = self.technical.analyze(klines)
        
        # 当前价格
        current_price = klines[-1].close if klines else 0
        
        # 价格变化
        if ticker:
            price_change = ticker.change_24h
            volume = ticker.volume_24h
        else:
            price_change = klines[-1].change_percent if klines else 0
            volume = sum(k.volume for k in klines[-6:]) if klines else 0  # 最近6根K线
        
        # 资金费率
        funding_rate = funding.funding_rate if funding else 0.0001
        
        # 市场情绪判断
        sentiment = self._analyze_sentiment(indicators, funding_rate)
        
        # 计算关键价位
        key_levels = self._calculate_key_levels(klines, indicators)
        
        # K线摘要
        kline_summary = self._generate_kline_summary(klines, indicators)
        
        # 获取相关新闻
        news = self.MOCK_NEWS.get(symbol, self.MOCK_NEWS["DEFAULT"])
        
        return MarketAnalysis(
            symbol=symbol,
            current_price=current_price,
            indicators=indicators,
            price_change_24h=price_change,
            volume_24h=volume,
            funding_rate=funding_rate,
            market_sentiment=sentiment,
            key_levels=key_levels,
            kline_summary=kline_summary,
            news_headlines=news
        )
    
    def _analyze_sentiment(
        self,
        indicators: TechnicalIndicators,
        funding_rate: float
    ) -> str:
        """分析市场情绪"""
        score = 0
        
        # RSI
        if indicators.rsi_14 > 70:
            score -= 2  # 超买
        elif indicators.rsi_14 < 30:
            score += 2  # 超卖
        elif indicators.rsi_14 > 50:
            score += 1
        else:
            score -= 1
        
        # MACD
        if indicators.macd_histogram > 0:
            score += 1
        else:
            score -= 1
        
        # 趋势
        if indicators.trend_status == "bullish":
            score += 2
        elif indicators.trend_status == "bearish":
            score -= 2
        
        # 资金费率
        if funding_rate > 0.001:
            score -= 1  # 多头拥挤
        elif funding_rate < -0.001:
            score += 1  # 空头拥挤
        
        if score >= 3:
            return "极度乐观"
        elif score >= 1:
            return "偏多"
        elif score <= -3:
            return "极度悲观"
        elif score <= -1:
            return "偏空"
        else:
            return "中性"
    
    def _calculate_key_levels(
        self,
        klines: List[Kline],
        indicators: TechnicalIndicators
    ) -> Dict[str, float]:
        """计算关键价位"""
        if not klines:
            return {}
        
        current = klines[-1].close
        recent_highs = [k.high for k in klines[-20:]]
        recent_lows = [k.low for k in klines[-20:]]
        
        return {
            "strong_resistance": max(recent_highs),
            "weak_resistance": indicators.bb_upper,
            "current_price": current,
            "weak_support": indicators.bb_lower,
            "strong_support": min(recent_lows),
            "sma_20": indicators.sma_20,
            "sma_50": indicators.sma_50
        }
    
    def _generate_kline_summary(
        self,
        klines: List[Kline],
        indicators: TechnicalIndicators
    ) -> str:
        """生成K线摘要文本"""
        if not klines:
            return "数据不足"
        
        current = klines[-1]
        prev = klines[-2] if len(klines) > 1 else current
        
        # 最近24小时统计（假设4小时K线）
        recent_24h = klines[-6:] if len(klines) >= 6 else klines
        high_24h = max(k.high for k in recent_24h)
        low_24h = min(k.low for k in recent_24h)
        change_24h = ((current.close - recent_24h[0].open) / recent_24h[0].open) * 100
        
        # 连续涨跌统计
        consecutive = 0
        direction = "涨" if klines[-1].close > klines[-1].open else "跌"
        for k in reversed(klines[:-1]):
            if (k.close > k.open) == (direction == "涨"):
                consecutive += 1
            else:
                break
        
        summary = f"""当前价格: {current.close:.2f}
24小时变化: {change_24h:+.2f}%
24小时区间: {low_24h:.2f} - {high_24h:.2f}
最新K线: {'阳线' if current.is_bullish else '阴线'} (涨幅 {current.change_percent:+.2f}%)
连续: {consecutive + 1}根{direction}线
RSI: {indicators.rsi_14:.1f} ({'超买' if indicators.rsi_14 > 70 else '超卖' if indicators.rsi_14 < 30 else '中性'})
MACD: {'多头' if indicators.macd_histogram > 0 else '空头'}信号
趋势: {indicators.trend_status}
均线状态: {indicators.ma_cross_status}"""
        
        return summary
    
    def format_context_for_ai(self, analysis: MarketAnalysis) -> str:
        """格式化为AI上下文"""
        indicators = analysis.indicators
        
        context = f"""## 交易对: {analysis.symbol}

### 价格信息
- 当前价格: {analysis.current_price:.4f}
- 24小时涨跌: {analysis.price_change_24h:+.2f}%
- 24小时成交量: {analysis.volume_24h:,.0f}

### 技术指标
- RSI(14): {indicators.rsi_14:.2f}
- MACD柱状图: {indicators.macd_histogram:+.6f}
- MA20: {indicators.sma_20:.4f}
- MA50: {indicators.sma_50:.4f}
- 布林带上轨: {indicators.bb_upper:.4f}
- 布林带下轨: {indicators.bb_lower:.4f}
- ATR(14): {indicators.atr_14:.4f}

### 趋势分析
- 趋势状态: {indicators.trend_status}
- 均线状态: {indicators.ma_cross_status}
- 波动率: {indicators.volatility_level}

### 市场情绪
- 资金费率: {analysis.funding_rate * 100:.4f}%
- 整体情绪: {analysis.market_sentiment}

### 关键价位
- 强阻力: {analysis.key_levels.get('strong_resistance', 0):.4f}
- 弱阻力: {analysis.key_levels.get('weak_resistance', 0):.4f}
- 当前价: {analysis.current_price:.4f}
- 弱支撑: {analysis.key_levels.get('weak_support', 0):.4f}
- 强支撑: {analysis.key_levels.get('strong_support', 0):.4f}

### K线摘要
{analysis.kline_summary}

### 相关新闻
"""
        for news in analysis.news_headlines[:3]:
            context += f"- {news}\n"
        
        return context


# 单例
_analyzer_instance: Optional[MarketAnalyzer] = None


def get_market_analyzer() -> MarketAnalyzer:
    """获取市场分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = MarketAnalyzer()
    return _analyzer_instance
