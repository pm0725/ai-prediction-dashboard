from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class TechnicalIndicators:
    """
    统一的技术指标数据模型
    合并了原 analyzer.py 和 data_aggregator.py 中的定义
    """
    # 移动平均线
    sma_20: float = 0.0
    sma_50: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    
    # RSI
    rsi_14: float = 50.0
    
    # MACD
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    
    # 布林带
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_width: float = 0.0
    
    # Keltner Channel / ATR
    atr_14: float = 0.0
    
    # 趋势状态
    trend_status: str = "neutral"  # "bullish", "bearish", "neutral"
    ma_cross_status: str = "none"  # "golden_cross", "death_cross", "none" (analyzer用"无交叉")
    
    # analyzer.py 特有字段
    volatility_level: str = "中等"
    
    # data_aggregator.py 特有字段
    # EMA快慢线
    ema_9: float = 0.0
    ema_21: float = 0.0
    ema_cross_status: str = ""
    
    # K线形态
    candlestick_patterns: List[str] = field(default_factory=list)
    
    # 信号冲突检测
    signal_conflicts: List[str] = field(default_factory=list)
    
    # 趋势线
    trend_lines: Dict[str, Any] = field(default_factory=dict)
    
    # 成交量分析
    volume_ratio: float = 1.0
    volume_status: str = "normal"
    
    # ADX
    adx: float = 0.0
    adx_status: str = ""
    
    # VWAP
    vwap: float = 0.0
    vwap_deviation: float = 0.0

    # V2.0 Pro: SMC & Volume Profile
    vp_hvn: Optional[float] = None  # High Volume Node (Value Area High/POC)
    vp_lvn: Optional[float] = None  # Low Volume Node (Vacuum Zone)
    order_blocks: List[Dict[str, Any]] = field(default_factory=list) # SMC OBs
    fvg_gaps: List[Dict[str, Any]] = field(default_factory=list) # Fair Value Gaps

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，优先兼容 analyzer.py 的输出格式"""
        return {
            "sma_20": round(self.sma_20, 4),
            "sma_50": round(self.sma_50, 4),
            "ema_12": round(self.ema_12, 4),
            "ema_26": round(self.ema_26, 4),
            "rsi_14": round(self.rsi_14, 2),
            "macd_line": round(self.macd_line, 6),
            "macd_signal": round(self.macd_signal, 6),
            "macd_histogram": round(self.macd_histogram, 6),
            "bb_upper": round(self.bb_upper, 4),
            "bb_middle": round(self.bb_middle, 4),
            "bb_lower": round(self.bb_lower, 4),
            "bb_width": round(self.bb_width, 4),
            "atr_14": round(self.atr_14, 4),
            "trend_status": self.trend_status,
            "ma_cross_status": self.ma_cross_status,
            "volatility_level": self.volatility_level,
            # 扩展字段
            "adx": round(self.adx, 2),
            "vwap": round(self.vwap, 4),
            "volume_ratio": round(self.volume_ratio, 2),
            "candlestick_patterns": self.candlestick_patterns,
            "signal_conflicts": self.signal_conflicts,
            "vp_hvn": self.vp_hvn,
            "vp_lvn": self.vp_lvn,
            "order_blocks": self.order_blocks,
            "fvg_gaps": self.fvg_gaps
        }
