"""
智链预测 - DeepSeek AI分析引擎
==============================
顶尖加密货币量化风控师 AI 服务封装

此模块封装了DeepSeek API的调用逻辑，专门用于加密货币合约预测分析。
主要功能：
1. 构建专业的系统提示词，定义AI角色为"顶尖加密货币量化风控师"
2. 接收市场数据并构建结构化的用户Prompt
3. 调用DeepSeek API获取分析结果（JSON格式）
4. 处理API错误、网络超时和响应解析

Author: 智链预测团队
Version: 1.0.0
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from openai import AsyncOpenAI, APIError, APITimeoutError, APIConnectionError
from pydantic import BaseModel, Field, validator
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# MED-6: Import cache service inside method to avoid circular import
# from app.services.cache_service import get_cached_analyzer


# ============================================================
# 数据模型定义
# ============================================================

class PredictionDirection(str, Enum):
    """预测方向枚举"""
    BULLISH = "看涨"      # 看涨
    BEARISH = "看跌"      # 看跌
    NEUTRAL = "震荡"      # 震荡/中性


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    EXTREME = "极高"



class EmptyResponseError(Exception):
    """API返回空响应异常"""
    pass


@dataclass
class KeyLevels:
    """关键价格水平"""
    strong_resistance: float      # 强阻力位
    weak_resistance: float        # 弱阻力位
    current_price: float          # 当前价格
    weak_support: float           # 弱支撑位
    strong_support: float         # 强支撑位


class AnalysisResult(BaseModel):
    """
    AI分析结果模型
    
    定义DeepSeek返回的JSON结构，包含预测、置信度、逻辑链等关键信息
    """
    # 基础信息
    symbol: str = Field(..., description="交易对符号")
    analysis_time: str = Field(..., description="分析时间戳")
    timeframe: str = Field(default="4h", description="分析时间周期")
    
    # 核心预测
    prediction: str = Field(..., description="预测方向：看涨/看跌/震荡")
    confidence: int = Field(..., ge=0, le=100, description="置信度(0-100)")
    
    # 分析逻辑
    reasoning: list[str] = Field(..., description="逻辑推理链，每条一个要点")
    
    # 关键价位
    key_levels: dict = Field(..., description="关键支撑阻力位")
    
    # 策略建议
    suggested_action: str = Field(..., description="建议操作")
    entry_zone: Optional[dict] = Field(None, description="入场区间")
    stop_loss: Optional[float] = Field(None, description="止损价位")
    take_profit: Optional[list[float]] = Field(None, description="止盈价位列表")
    
    # 风险评估
    risk_level: str = Field(..., description="风险等级")
    risk_warning: list[str] = Field(..., description="风险警告列表")
    
    # 摘要
    summary: str = Field(..., description="中文分析摘要(100字内)")
    
    # [新增] AI 配置报告 (用于前端展示目前生效的配置)
    ai_model: Optional[str] = Field(None, description="使用的AI模型")
    ai_prompt_template: Optional[str] = Field(None, description="使用的提示词模板名称或摘要")
    
    # 透传上下文 (非AI生成，由后端填充)
    trend_context: Optional[dict] = Field(None, description="趋势周期上下文")
    order_book_context: Optional[dict] = Field(None, description="订单簿上下文")
    on_chain_context: Optional[dict] = Field(None, description="链上数据上下文")

    @validator('prediction')
    def validate_prediction(cls, v):
        # 统一归一化为标准值，容忍带额外描述的变体
        v_low = v.lower()
        if any(x in v_low for x in ['看涨', 'bull']): return '看涨'
        if any(x in v_low for x in ['看跌', 'bear']): return '看跌'
        return '震荡'


# ============================================================
# 系统提示词定义
# ============================================================

SYSTEM_PROMPT = """# Role: 智链机构级量化分析师 (Institutional Quant Strategist)
你是一个具有多年顶级对冲基金经验的加密货币策略专家。你的任务是基于提供的专业级数据上下文，生成具备“机构逻辑”的深度合约策略。

## 核心策略框架 (V2.0 Pro)

### 1. 入场锚定 (SMC - Smart Money Concepts)
- **机构订单块 (Order Block)**: 优先在 `smc.order_blocks` 标识的 OB 区域寻找入场锚点。OB 是机构真实留下足迹的位置。
- **缺口回补 (FVG)**: 参考 `smc.fvg_gaps`，价格往往会回测并填补 FVG 缺口。入场位应设在 OB 或 FVG 的关键折返点。

### 2. 止损布局 (VPVR - 成交真空区检测)
- **流动性屏障**: 止损位必须避开 `vpvr.vacuum_lvn` (成交真空区)。真空区缺乏买卖盘，价格在此会极速穿行，止损极易失效。
- **锚定 POC/HVN**: 将止损设在 `vpvr.poc_hvn` (成交密集区) 的远端或下一个结构性支撑/阻力之外。
- **动态 ATR 约束**: 止损距离必须至少为 `1.5 * atr_14`。

### 3. 仓位协议 (阶梯式止盈 & 减仓)
- **1:1 减仓协议**: 强制设置 `take_profit[0]` (TP1) 在盈亏比 1:1 处。建议在此平仓 50% 并将止损移至开仓位（保本）。
- **专业盈亏比**: 排除 TP1 后，后续目标的最终盈亏比 (RRR) 必须 >= 1.5。

### 4. 趋势共振 (MTF alignment)
- **大周期定性**: 所有的建议必须参考 `trend_context` (4H/Daily)。禁止在 4H 强烈看跌的情况下给出无风险提示的 1H/15M 做多信号。

## 逻辑一致性硬性规则 (Hard Constraints)
- **做多**: `TP > Entry > SL` 且 `Entry <= Current Price`。
- **做空**: `TP < Entry < SL` 且 `Entry >= Current Price`。
- **冲突拦截**: 若 `reasoning` 过程与价位逻辑矛盾（例如判定看涨但点位设为向下突破），必须降级预测为“震荡/观望”。

## 输出要求 (Strict JSON)
`reasoning` 数组必须体现 [结构观察 -> 筹码分布 -> 止损安全评估 -> 策略执行策略]。

```json
{
  "symbol": "...",
  "prediction": "看涨|看跌|震荡",
  "confidence": 0-100,
  "reasoning": ["...", "..."],
  "entry_zone": {"low": 0, "high": 0},
  "stop_loss": 0,
  "take_profit": [0, 0, 0], 
  "risk_level": "低|中|高|极高",
  "summary": "一句简短建议 (e.g. OB挂单, FVG回补入场)"
}
```
"""


# ============================================================
# DeepSeek 分析师类
# ============================================================

class DeepSeekAnalyst:
    """
    DeepSeek AI 分析师
    
    封装与DeepSeek API的交互，提供专业的加密货币合约分析能力。
    
    使用示例:
        >>> analyst = DeepSeekAnalyst(api_key="your-api-key")
        >>> result = analyst.analyze_market(
        ...     symbol="ETHUSDT",
        ...     context_data={
        ...         "kline_summary": "最近24小时价格从2500上涨至2650...",
        ...         "funding_rate": 0.0012,
        ...         "news_headlines": ["ETH ETF资金持续流入", "..."]
        ...     }
        ... )
        >>> print(result.prediction, result.confidence)
    
    Attributes:
        client: OpenAI客户端实例（DeepSeek兼容OpenAI API格式）
        model: 使用的模型名称
        system_prompt: 系统提示词
        temperature: 生成温度，控制输出随机性
        max_tokens: 最大输出token数
    """
    
    # DeepSeek API基础URL
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    
    # 默认模型 (从环境变量读取)
    DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 300.0
    ):
        """
        初始化DeepSeek分析师
        
        Args:
            api_key: DeepSeek API密钥，如不提供则从环境变量DEEPSEEK_API_KEY读取
            model: 模型名称，默认为deepseek-chat
            temperature: 生成温度(0-1)，越高越随机，默认0.7
            max_tokens: 最大输出token数，默认12000
            timeout: API请求超时时间（秒），默认300秒
        
        Raises:
            ValueError: 当未提供API密钥且环境变量中也没有时抛出
        """
        # 获取API密钥
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "未提供DeepSeek API密钥。"
                "请通过参数传入或设置环境变量 DEEPSEEK_API_KEY"
            )
        
        # 初始化异步客户端 (DeepSeek兼容OpenAI API格式)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.DEEPSEEK_BASE_URL,
            timeout=timeout
        )
        
        self.model = model
        self.system_prompt = SYSTEM_PROMPT
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"DeepSeek分析师初始化完成 | 模型: {model} | Max Tokens: {max_tokens}")
    
    def _build_reasoner_prompt(
        self,
        symbol: str,
        context_data: dict[str, Any]
    ) -> str:
        """
        构建 DeepSeek Reasoner (R1) 专用 Prompt
        
        特点: 
        - 减少角色扮演，提供纯数据
        - 强调逻辑推理链 (Chain of Thought)
        - 后置格式约束
        """
        # 1. 基础数据准备
        current_time = datetime.now().isoformat()
        timeframe = context_data.get("timeframe", "4h")
        timeframe_cn = {
            "15m": "15分钟", "1h": "1小时", "4h": "4小时", "1d": "日线", "1w": "周线"
        }.get(timeframe, timeframe)
        
        # ===== K 线数据 =====
        raw_klines = context_data.get("klines", [])
        kline_text = ""
        if raw_klines:
            # P2 修复: 排除最后一根未闭合的K线，避免半完成数据误导AI判断
            completed_klines = raw_klines[:-1] if len(raw_klines) > 1 else raw_klines
            klines = completed_klines[-300:] # Increased from 100 to 300
            kline_text = json.dumps([{
                't': k['timestamp'], 'o': k['open'], 'h': k['high'],
                'l': k['low'], 'c': k['close'], 'v': k['volume']
            } for k in klines])
            
        # ===== 趋势 K 线数据 (New) =====
        trend_context = context_data.get("trend_context", {})
        raw_trend_klines = trend_context.get("klines", [])
        trend_kline_text = ""
        if raw_trend_klines:
            # 取最后60根大周期K线 (足够看清整体结构)
            trend_klines = raw_trend_klines[-60:]
            trend_kline_text = json.dumps([{
                't': k['timestamp'], 'o': k['open'], 'h': k['high'],
                'l': k['low'], 'c': k['close']
            } for k in trend_klines])
        
        # ===== K 线预计算统计 =====
        kline_stats = ""
        if raw_klines and len(raw_klines) >= 5:
            recent = raw_klines[-5:]
            consecutive = 0
            direction = "阳" if recent[-1]['close'] >= recent[-1]['open'] else "阴"
            for k in reversed(recent):
                if (k['close'] >= k['open'] and direction == "阳") or (k['close'] < k['open'] and direction == "阴"):
                    consecutive += 1
                else:
                    break
            vols = [k.get('volume', 0) for k in raw_klines[-20:]]
            vol_avg = sum(vols) / len(vols) if vols else 1
            vol_recent = sum(vols[-3:]) / 3 if len(vols) >= 3 else vol_avg
            vol_trend = "放量" if vol_recent > vol_avg * 1.3 else ("缩量" if vol_recent < vol_avg * 0.7 else "量能平稳")
            kline_stats = f"连续{consecutive}根{direction}线 | 近期{vol_trend} | 最近5根波动幅度: {sum(abs(k['high']-k['low'])/k['open']*100 for k in recent)/5:.2f}%"
            
        # ===== 技术指标（完整版）=====
        indicators = {
            "rsi": context_data.get("rsi"),
            "macd": context_data.get("macd"),
            "ma_status": context_data.get("ma_status"),
            "ema_status": context_data.get("ema_status"),
            "bollinger": context_data.get("bollinger"),
            "atr": context_data.get("atr"),
            "rvol": context_data.get("volume_ratio", 1.0),
            "trend_lines": context_data.get("trend_lines"),
            "candlestick_patterns": context_data.get("candlestick_patterns"),
            "signal_conflicts": context_data.get("signal_conflicts")
        }
        
        # ===== 机构数据 =====
        institutional = {
            "whale_activity": context_data.get("whale_activity"),
            "liquidity_gaps": context_data.get("liquidity_gaps"),
            "volatility_score": context_data.get("volatility_score"),
            "order_book": context_data.get("order_book")
        }
        
        # ===== 基本面数据 (CoinGecko) =====
        fundamentals = context_data.get("fundamental_data")
        fundamental_text = ""
        if fundamentals:
            fundamental_text = f"""
- 开发者评分: {fundamentals.get('developer_score', 'N/A')}
- 社区评分: {fundamentals.get('community_score', 'N/A')}
- 公众关注度: {fundamentals.get('public_interest_score', 'N/A')}
- 24h价格变化: {fundamentals.get('price_change_24h', 0):.2f}%
- 距历史高点: {fundamentals.get('ath_change_percentage', 0):.2f}%
- 24h成交量: ${fundamentals.get('total_volume', 0):,.0f}
- 市值: ${fundamentals.get('market_cap', 0):,.0f}
""".strip()
        
        # ===== 合约数据 =====
        derivatives = {}
        if context_data.get("funding_rate") is not None:
            derivatives["funding_rate"] = context_data["funding_rate"]
        if context_data.get("funding_rate_history"):
            derivatives["funding_rate_trend"] = context_data["funding_rate_history"]
        if context_data.get("open_interest") is not None:
            derivatives["open_interest"] = context_data["open_interest"]
        if context_data.get("oi_change"):
            derivatives["oi_change_24h"] = context_data["oi_change"]
        if context_data.get("long_short_ratio") is not None:
            derivatives["long_short_ratio"] = context_data["long_short_ratio"]

        # ===== 构建 Prompt =====
        parts = [
            f"[数据上下文]",
            f"交易对: {symbol}",
            f"时间: {current_time}",
            f"周期: {timeframe} ({timeframe_cn})",
            f"当前价格: {context_data.get('current_price', 'N/A')}",
        ]
        
        if kline_stats:
            parts.append(f"K线统计: {kline_stats}")
        
        parts.extend([
            f"\n[市场数据 (OHLCV)]",
            kline_text,
        ])
        
        if trend_kline_text:
            parts.extend([
                f"\n[大趋势数据 (Trend OHLC)]",
                trend_kline_text
            ])
            
        parts.extend([
            f"\n[技术指标]",
            json.dumps(indicators, indent=2, ensure_ascii=False),
        ])
        
        if derivatives:
            parts.extend([
                f"\n[合约/衍生品数据]",
                json.dumps(derivatives, indent=2, ensure_ascii=False)
            ])
            
        if fundamental_text:
            parts.extend([
                f"\n[基本面数据 (CoinGecko)]",
                fundamental_text
            ])

        
        parts.extend([
            f"\n[机构数据]",
            json.dumps(institutional, indent=2, ensure_ascii=False),
        ])
        
        # 市场情绪
        sentiment = context_data.get("market_sentiment")
        if sentiment:
            parts.append(f"\n[市场情绪]\n{sentiment}")
        
        # 恐惧贪婪指数
        fng = context_data.get("fear_greed_index")
        if fng:
            parts.append(f"\n[恐惧贪婪指数]\n指数: {fng.get('value', 50)} ({fng.get('classification', '中性')})")
        
        # 新闻
        news = context_data.get("news_headlines", [])
        if news:
            parts.append(f"\n[新闻简报]")
            for n in news[:5]:
                parts.append(f"- {n}")
        
        # 枢轴点 + 波段高低
        pivot = context_data.get("pivot_points")
        if pivot:
            parts.extend([f"\n[枢轴点]", json.dumps(pivot, indent=2)])
        swing = context_data.get("swing_levels")
        if swing:
            parts.extend([f"\n[波段高低点]", json.dumps(swing, indent=2)])
        
        # VPVR
        ob = context_data.get("order_book", {})
        vpvr = ob.get("vpvr") if ob else None
        if vpvr:
            cp = context_data.get('current_price', 0)
            parts.append(f"\n[筹码分布 VPVR]")
            parts.append(f"POC(控制点): {vpvr['poc']} | 价值区间: {vpvr['val']}-{vpvr['vah']}")
            parts.append(f"当前价{'高于' if cp > vpvr.get('poc', cp) else '低于'}POC")
        
        # 趋势周期
        tc = context_data.get("trend_context")
        if tc:
            parts.append(f"\n[趋势周期背景]")
            parts.append(f"趋势状态: {tc.get('trend_status')} | RSI: {tc.get('rsi', 0):.1f} | EMA21: {tc.get('ema_21', 0):.2f}")
            parts.append(f"走势: {tc.get('summary', '')}")
        
        # 清算价位
        liq = context_data.get("liquidation_levels")
        if liq:
            parts.append(f"\n[理论清算价位]")
            parts.append(f"多头爆仓(50x): {liq.get('long_liq', {}).get('50x', 'N/A')} | 空头爆仓(50x): {liq.get('short_liq', {}).get('50x', 'N/A')}")
        
        # BTC上下文（山寨币用）
        btc_ctx = context_data.get("btc_context")
        if btc_ctx:
            parts.append(f"\n[BTC 大盘走势]")
            parts.append(f"BTC 价格: {btc_ctx.get('price')} | 趋势: {btc_ctx.get('trend')} | RSI: {btc_ctx.get('rsi', 'N/A')}")
        
        # ===== 分析指令 + 硬性规则 =====
        atr_val = context_data.get('atr', 0)
        rsi_val = context_data.get('rsi', 50)
        
        parts.extend([
            f"\n[分析请求]",
            f"请分析以上 {symbol} 的数据，判断后续{timeframe_cn}走势和交易机会。",
            f"请使用你的推理能力进行逐步分析。",
            f"**重要: 保持内部推理简洁，确保最终 JSON 不被截断。所有输出使用中文。**",
            f"",
            f"分析步骤:",
            f"1. 根据 OHLCV、EMA、MA 分析市场结构与趋势。",
            f"2. 使用 RSI、MACD、相对成交量评估动能。",
            f"3. 通过订单簿、枢轴点、流动性真空区识别关键支撑/阻力位。",
            f"4. 结合合约数据（资金费率、持仓量、多空比）判断市场偏见。",
            f"5. 检测机构行为痕迹（巨鲸活动）。",
            f"6. 综合所有信号制定交易计划。",
            f"",
            f"**硬性规则（必须遵守）**：",
            f"- 做多: TP > Entry > SL，入场价 ≤ 当前价格",
            f"- 做空: SL > Entry > TP，入场价 ≥ 当前价格",
        ])
        
        if atr_val > 0:
            parts.append(f"- ATR动态止损: 当前ATR={atr_val:.2f}，止损距离 ≥ 1.5*ATR={atr_val*1.5:.2f}，入场区间宽 ≈ 0.5*ATR={atr_val*0.5:.2f}")
        
        if rsi_val > 65:
            parts.append(f"- ⚠️ RSI={rsi_val:.1f} 超买，禁止市价追多，请寻找回调入场")
        elif rsi_val < 35:
            parts.append(f"- ⚠️ RSI={rsi_val:.1f} 超卖，禁止市价追空，请寻找反弹入场")
        
        if tc and tc.get('trend_status'):
            parts.append(f"- 多周期共振: 趋势周期为{tc['trend_status']}，禁止逆势激进操作")
        
        vol_score = context_data.get("volatility_score", 0)
        if vol_score > 70:
            parts.append(f"- ⚠️ 大行情风险指数={vol_score:.0f}/100 (极高)，必须在 risk_warning 中发出变盘警告")
        
        parts.extend([
            f"",
            f"[输出要求]",
            f"推理完成后，严格按照以下 JSON 格式输出（所有文本使用中文）：",
            f"{{",
            f'  "symbol": "{symbol}",',
            f'  "analysis_time": "{current_time}",',
            f'  "timeframe": "{timeframe}",',
            f'  "prediction": "看涨/看跌/震荡",',
            f'  "confidence": 0-100,',
            f'  "reasoning": ["分析要点1", "分析要点2", "分析要点3"],',
            f'  "key_levels": {{ "strong_resistance": 0, "current_price": 0, "strong_support": 0 }},',
            f'  "suggested_action": "做多/做空/观望",',
            f'  "entry_zone": {{ "low": 0, "high": 0 }},',
            f'  "stop_loss": 0,',
            f'  "take_profit": [0, 0],',
            f'  "risk_level": "低/中/高",',
            f'  "risk_warning": ["风险提示1"],',
            f'  "summary": "分析摘要"',
            f"}}",
        ])
        
        return "\n".join(parts)

    def _build_user_prompt(
        self,
        symbol: str,
        context_data: dict[str, Any]
    ) -> str:

        """
        构建用户Prompt
        
        将交易对符号和上下文数据整合为结构化的用户提示词。
        
        Args:
            symbol: 交易对符号，如 "ETHUSDT"
            context_data: 上下文数据字典，可包含以下字段：
                - kline_summary: K线数据摘要
                - current_price: 当前价格
                - funding_rate: 资金费率
                - open_interest: 持仓量
                - volume_24h: 24小时成交量
                - rsi: RSI指标值
                - macd: MACD指标状态
                - ma_status: 均线状态
                - news_headlines: 新闻标题列表
                - market_sentiment: 市场情绪
        
        Returns:
            str: 格式化后的用户Prompt
        """

        # 获取当前时间
        current_time = datetime.now().isoformat()
        
        # 获取分析周期 (从上下文中读取，默认4h)
        timeframe = context_data.get("timeframe", "4h")
        timeframe_cn = {
            "1h": "1小时", "4h": "4小时", "1d": "日线", "1w": "周线"
        }.get(timeframe, timeframe)
        
        # 获取分析偏好
        prefs = context_data.get("user_preferences", {})
        depth_level = prefs.get("depth", 2) # 1: quick, 2: standard, 3: deep
        
        # 1. 动态精简 K 线数据 (Token 效率核心)
        # 根据深度决定传给 AI 的历史 K 线长度
        kline_limit = {1: 30, 2: 70, 3: 150}.get(depth_level, 70)
        
        # 提取 K 线摘要 (假设 context_data['klines'] 是原始列表)
        raw_klines = context_data.get("klines", [])
        # P2 修复: 排除最后一根未闭合的K线
        completed_klines = raw_klines[:-1] if len(raw_klines) > 1 else raw_klines
        if len(completed_klines) > kline_limit:
            klines_to_send = completed_klines[-kline_limit:]
            kline_summary = f"最近 {kline_limit} 根分时线: Open={klines_to_send[0]['open']}, Close={klines_to_send[-1]['close']}, "
            kline_summary += f"High={max(k['high'] for k in klines_to_send)}, Low={min(k['low'] for k in klines_to_send)}"
        else:
            kline_summary = context_data.get("kline_summary", "保持当前预测")

        # 2. 构建高密度技术脉络 (Tech Pulse)
        technical_pulse = {
            "p": context_data.get("current_price"),
            "rsi": round(context_data.get("rsi", 50), 2),
            "macd": context_data.get("macd", "0/0/0"),
            "ema": context_data.get("ema_status", "未确认"),
            "trend": context_data.get("ma_status", "neutral"),
            "vol": context_data.get("volume_24h", "n/a"),
            "rvol": context_data.get("volume_ratio", 1.0),
            "vol_status": context_data.get("volume_status", "normal"),
            "atr": round(context_data.get("atr", 0), 2),
            "adx": round(context_data.get("adx", 0), 1),
            "adx_status": context_data.get("adx_status", ""),
            "vwap": round(context_data.get("vwap", 0), 2),
            "vwap_dev": f"{context_data.get('vwap_deviation', 0):+.2f}%"
        }

        # 3. 组装 Prompt
        prompt_parts = [
            f"## [Context] {symbol} @ {datetime.now().isoformat()} (TF: {context_data.get('timeframe', '4h')})",
            f"### [Price & K-lines]\n{kline_summary}",
            f"### [Technical Pulse]\n{json.dumps(technical_pulse)}",
        ]
        
        # 添加精简新闻 (所有 depth 级别)
        news = context_data.get("news_headlines", [])
        if news:
            prompt_parts.append(f"### [Top Headlines]\n" + "\n".join([f"- {h}" for h in news[:3]]))

        # ========== 深度上下文 (按 depth 级别门控) ==========
        _inject_deep = depth_level >= 2      # 标准 + 深度
        _inject_advanced = depth_level >= 3   # 仅深度

        # ========== 新增: 合约数据 (资金费率趋势 + 多空比) ==========
        if _inject_deep:
            contract_parts = []
            fr = context_data.get("funding_rate")
            fr_history = context_data.get("funding_rate_history")
            if fr is not None:
                contract_parts.append(f"- 当前资金费率: {fr*100:.4f}%")
            if fr_history and isinstance(fr_history, dict):
                contract_parts.append(f"- 费率趋势: {fr_history.get('trend', 'N/A')} (均值: {fr_history.get('avg_24', 0)*100:.4f}%, 近期: {fr_history.get('recent_avg', 0)*100:.4f}%)")
            ls_ratio = context_data.get("long_short_ratio")
            if ls_ratio is not None:
                ls_desc = "多头优势" if ls_ratio > 1.2 else ("空头优势" if ls_ratio < 0.8 else "多空平衡")
                contract_parts.append(f"- 多空比: {ls_ratio:.3f} ({ls_desc})")
            oi = context_data.get("open_interest")
            if oi:
                contract_parts.append(f"- 持仓量: {oi:.2f}")
            if contract_parts:
                prompt_parts.append("\n### 合约数据 (Derivatives)")
                prompt_parts.extend(contract_parts)

        # ========== 新增: BTC 大盘上下文 ==========
        btc_ctx = context_data.get("btc_context")
        if _inject_deep and btc_ctx:
            prompt_parts.append("\n### BTC 大盘背景")
            prompt_parts.append(f"- BTC 价格: {btc_ctx.get('price')} | 涨跌幅: {btc_ctx.get('change_pct', 0):+.2f}%")
            prompt_parts.append(f"- BTC 趋势: {btc_ctx.get('trend')} | RSI: {btc_ctx.get('rsi', 'N/A')}")
            if btc_ctx.get('trend') == 'bearish':
                prompt_parts.append("- ⚠️ BTC 走弱，山寨币做多需谨慎")

        # ========== 新增: K线形态识别 ==========
        if _inject_deep and "candlestick_patterns" in context_data and context_data["candlestick_patterns"]:
            prompt_parts.append("\n### K线形态识别")
            for pattern in context_data["candlestick_patterns"]:
                prompt_parts.append(f"- ⚠️ {pattern}")
        
        # ========== 新增: 信号冲突警告 ==========
        if _inject_deep and "signal_conflicts" in context_data and context_data["signal_conflicts"]:
            prompt_parts.append("\n### ⚠️ 信号冲突提醒")
            for conflict in context_data["signal_conflicts"]:
                prompt_parts.append(f"- 🔴 {conflict}")
        
        # ========== 新增: 趋势线 (Trend Lines) ==========
        if _inject_deep and "trend_lines" in context_data and context_data["trend_lines"]:
            tl = context_data["trend_lines"]
            prompt_parts.append("\n### 自动趋势线识别 (Trend Lines)")
            
            res = tl.get('resistance_line')
            if res:
                dist = res.get('distance_pct', 0)
                prompt_parts.append(f"- 阻力线: 当前价位 {res.get('current_value')}, 距离 {dist:.2f}%")
                
            sup = tl.get('support_line')
            if sup:
                dist = sup.get('distance_pct', 0)
                prompt_parts.append(f"- 支撑线: 当前价位 {sup.get('current_value')}, 距离 {dist:.2f}%")
                
            breakout = tl.get('breakout')
            if breakout == 'bullish_breakout':
                prompt_parts.append("- ⚠️ 信号: 向上突破阻力线 (Bullish Breakout)")
            elif breakout == 'bearish_breakout':
                prompt_parts.append("- ⚠️ 信号: 向下跌破支撑线 (Bearish Breakout)")
            elif breakout == 'fakeout':
                prompt_parts.append("- ⚠️ 信号: 疑似假突破 (Fakeout)")

        # 添加恐惧贪婪指数 (新增)
        if _inject_deep and "fear_greed_index" in context_data and context_data["fear_greed_index"]:
            fng = context_data["fear_greed_index"]
            prompt_parts.append(f"\n### 市场情绪 (Fear & Greed)")
            prompt_parts.append(f"- 指数: {fng.get('value')} ({fng.get('classification')})")
            if fng.get('value', 50) < 20:
                prompt_parts.append("- 💡注意: 市场极度恐慌，可能有超跌反弹机会")
            elif fng.get('value', 50) > 80:
                prompt_parts.append("- 💡注意: 市场极度贪婪，警惕回调风险")

        # 添加市场深度 (增强版)
        if _inject_deep and "order_book" in context_data and context_data["order_book"]:
            ob = context_data["order_book"]
            prompt_parts.append("\n### 市场深度 (Order Book)")
            prompt_parts.append(f"- 多空挂单比: {ob.get('bid_ask_ratio', 0):.2f}")
            prompt_parts.append(f"- 短期压力状态: {ob.get('nearby_pressure', 'unknown')}")
            prompt_parts.append(f"- 主力支撑墙: {ob.get('major_support', {}).get('price', 0)} (量: {ob.get('major_support', {}).get('volume', 0):.2f})")
            prompt_parts.append(f"- 主力阻力墙: {ob.get('major_resistance', {}).get('price', 0)} (量: {ob.get('major_resistance', {}).get('volume', 0):.2f})")
            
            # 显示大单
            if ob.get('large_bids'):
                prompt_parts.append("- 🟢 大额买单:")
                for order in ob['large_bids']:
                    prompt_parts.append(f"  * 价格 {order['price']}: {order['volume']} BTC")
            if ob.get('large_asks'):
                prompt_parts.append("- 🔴 大额卖单:")
                for order in ob['large_asks']:
                    prompt_parts.append(f"  * 价格 {order['price']}: {order['volume']} BTC")
            
            # 显示 VPVR
            if "vpvr" in ob:
                vpvr = ob["vpvr"]
                prompt_parts.append("\n- 📊 筹码分布 (VPVR):")
                prompt_parts.append(f"  * POC (控制点/最强支撑阻力): {vpvr['poc']}")
                prompt_parts.append(f"  * 价值区间 (70%成交区): {vpvr['val']} - {vpvr['vah']}")
                prompt_parts.append(f"  * 状态: 当前价{'高于' if context_data.get('current_price', 0) > vpvr['poc'] else '低于'} POC")
        
        # 添加清算风险估算 (新增)
        if _inject_advanced and "liquidation_levels" in context_data:
            liq = context_data["liquidation_levels"]
            prompt_parts.append("\n### 理论清算风险 (Liquidation Map)")
            prompt_parts.append("提示：若价格触及以下区间，可能引发强制平仓导致行情加速。")
            
            # 结合持仓量分析
            oi = context_data.get("open_interest", 0)
            if oi > 5000: # 假设 > 5000 BTC 为高持仓
                prompt_parts.append(f"- ⚠️ 当前持仓量处于高位 ({oi:.2f} BTC)，爆仓波动将更剧烈")
                
            prompt_parts.append("- 多头爆仓价 (下跌风险):")
            prompt_parts.append(f"  * 50x杠杆: {liq['long_liq']['50x']:.2f}")
            prompt_parts.append(f"  * 20x杠杆: {liq['long_liq']['20x']:.2f}")
            
            prompt_parts.append("- 空头爆仓价 (上涨风险):")
            prompt_parts.append(f"  * 50x杠杆: {liq['short_liq']['50x']:.2f}")
            prompt_parts.append(f"  * 20x杠杆: {liq['short_liq']['20x']:.2f}")

        # 添加趋势周期 (新增)
        if _inject_advanced and "trend_context" in context_data and context_data["trend_context"]:
            tc = context_data["trend_context"]
            prompt_parts.append(f"\n### 趋势周期背景 ({tc.get('summary', '').split(' ')[0]})") # 取摘要的时间部分
            prompt_parts.append(f"- 趋势状态: {tc.get('trend_status', 'unknown')}")
            prompt_parts.append(f"- 趋势RSI: {tc.get('rsi', 0):.2f}")
            prompt_parts.append(f"- 趋势EMA21: {tc.get('ema_21', 0):.2f}")
            prompt_parts.append(f"- 趋势BB宽: {tc.get('bb_width', 0):.2%}")
            
            patterns = tc.get('candlestick_patterns', [])
            if patterns:
                 prompt_parts.append(f"- 趋势形态: {', '.join(patterns)}")
            
            prompt_parts.append(f"- 走势简述: {tc.get('summary', '')}")
            
        # ========== 新增: 硬核支撑/阻力数据 (Pivot & Swing) ==========
        if _inject_advanced and "pivot_points" in context_data and context_data["pivot_points"]:
            pp = context_data["pivot_points"]
            prompt_parts.append("\n### 关键支撑/阻力位数据 (Key S/R Levels)")
            
            # Classic Pivot
            cl = pp.get("classic", {})
            prompt_parts.append(f"- **Classic Pivot**: P={cl.get('p')} | R1={cl.get('r1')}, R2={cl.get('r2')} | S1={cl.get('s1')}, S2={cl.get('s2')}")
            
            # Fibonacci Pivot
            fi = pp.get("fibonacci", {})
            prompt_parts.append(f"- **Fibonacci Pivot**: P={fi.get('p')} | R1={fi.get('r1')}, S1={fi.get('s1')} (0.382) | R2={fi.get('r2')}, S2={fi.get('s2')} (0.618)")
            
        if _inject_advanced and "swing_levels" in context_data and context_data["swing_levels"]:
            sl = context_data["swing_levels"]
            prompt_parts.append(f"- **近期波段高低点 (Swing High/Low)**: High={sl.get('recent_high')}, Low={sl.get('recent_low')}")

        # ========== 新增: 机构级大行情预警 (Institutional Warning) ==========
        vol_score = context_data.get("volatility_score", 0)
        whale_data = context_data.get("whale_activity")
        gaps = context_data.get("liquidity_gaps")
        
        if vol_score > 30 or whale_data or gaps:
            prompt_parts.append(f"\n### ⚠️ 机构级大行情预警 (Institutional Alert)")
            prompt_parts.append(f"- **大行情风险指数 (Volatility Score)**: {vol_score:.1f}/100")
            
            if vol_score > 70:
                prompt_parts.append("  🚨 **极度危险**: 变盘在即，布林带收口或主力异动强烈！")
            elif vol_score > 30:
                prompt_parts.append("  ⚠️ **活跃状态**: 市场波动加剧，主力开始活动。")
                
            if whale_data:
                wr = whale_data.get('whale_ratio', 0)
                net = whale_data.get('net_whale_vol', 0)
                prompt_parts.append(f"- **巨鲸活动 (Whale Activity)**:")
                prompt_parts.append(f"  * 大单成交占比: {wr*100:.1f}%")
                prompt_parts.append(f"  * 大单净流量: {net:+.2f} USD")
                if wr > 0.4 and net > 0:
                    prompt_parts.append("  🟢 **信号**: 巨鲸正在吸筹 (Accumulation)")
                elif wr > 0.4 and net < 0:
                    prompt_parts.append("  🔴 **信号**: 巨鲸正在出货 (Distribution)")
            
            if gaps:
                prompt_parts.append(f"- **流动性真空 (Liquidity Gaps)**:")
                for gap in gaps:
                    if gap == "upward_liquidity_gap":
                        prompt_parts.append("  🚀 **上方真空**: 阻力薄弱，价格易暴拉")
                    elif gap == "downward_liquidity_gap":
                        prompt_parts.append("  📉 **下方真空**: 支撑薄弱，价格易暴跌")
        
        # 添加分析指令 (增强版)
        prompt_parts.extend([
            "",
            "## 分析任务",
            f"请基于以上数据，对 **{symbol}** 的后续{timeframe_cn}走势进行专业分析。",
            "按照规定的JSON格式输出完整分析结果。",
            "",
            "**重要分析要点**：",
            "1. **主力墙挂单**：请参考 '市场深度' 中的主力支撑/阻力墙，将入场位设置在墙的前方(Front-Run)。",
            "2. **ATR动态止损**：止损距离应至少为 1.5倍 ATR，入场区间宽度建议 0.5倍 ATR。",
            "3. **K线形态优先**：如有反转形态，需重点评估其可靠性",
            "4. **信号冲突处理**：如存在指标冲突，需明确说明并降低置信度",
            "5. **多周期共振 (强制)**：若趋势周期(Trend Context)看跌(Price < EMA21)，禁止激进做多；若看涨(Price > EMA21)，禁止激进做空。",
            "6. **关注机构信号**：若'大行情风险指数' > 70，必须在 Risk Warning 中发出变盘警告；若存在'流动性真空'，目标位可适当看远。",
            "",
            "**置信度分档**：",
            "- 50-60%：信号较弱或存在冲突，建议观望",
            "- 60-70%：有一定依据，轻仓操作",
            "- 70-80%：多重信号共振，正常仓位",
            "- 80%+：强烈信号，可适当加仓",
            "",
            "2. 所有价格保留合适的小数位",
            "3. reasoning数组至少包含3-5条分析逻辑",
            "4. risk_warning必须列出可能导致判断失效的风险因素"
        ])

        # ========== 注入用户偏好 (复用 L278 的 prefs) ==========
        risk_pref = prefs.get("risk", "moderate")

        # ========== 智能入场与回调逻辑 ==========
        rsi_val = context_data.get('rsi', 50)
        if rsi_val > 65:
             prompt_parts.append("\n**⚠️ 智能入场提示**：当前RSI超买(>65)，**禁止建议市价追多**。请寻找下方支撑位(EMA/POC)进行回调接多建议。")
        elif rsi_val < 35:
             prompt_parts.append("\n**⚠️ 智能入场提示**：当前RSI超卖(<35)，**禁止建议市价追空**。请寻找上方阻力位进行反弹做空建议。")
        
        atr_val = context_data.get('atr', 0)
        if atr_val > 0:
             prompt_parts.append(f"**💡 ATR建议**：当前ATR={atr_val:.2f}。建议入场区间宽度约 {atr_val * 0.5:.2f}，止损距离约 {atr_val * 1.5:.2f}。")

        # RVol 智能提示 (新增)
        rvol = context_data.get("volume_ratio", 1.0)
        if rvol > 2.0:
            prompt_parts.append(f"**🔥 放量提醒**：当前相对成交量 (RVol) 为 {rvol:.2f} (Ultra High)，若突破关键位则有效性极高。")
        elif rvol < 0.8:
            prompt_parts.append(f"**⚠️ 缩量提醒**：当前相对成交量 (RVol) 仅 {rvol:.2f} (Low)，警惕诱多/诱空 (Fakeout)。")

        prompt_parts.append("\n**用户偏好设置 (必须遵守)**：")

        
        # 风险偏好
        if risk_pref == "conservative":
            prompt_parts.append("- **风格**: 保守稳健。优先考虑资金安全，严格控制风险。只有在信号极强时才建议入场。止损设置应偏紧。")
        elif risk_pref == "aggressive":
            prompt_parts.append("- **风格**: 激进进取。寻找高盈亏比机会，可接受适度风险。止损可适当放宽以应对波动。")
        else:
            prompt_parts.append("- **风格**: 均衡。在风险和收益之间寻找平衡。")

        # 分析深度
        if depth_level == 1:
            prompt_parts.append("- **深度**: 简明扼要。重点关注关键点位和核心逻辑，忽略次要细节。")
        elif depth_level == 3:
            prompt_parts.append("- **深度**: 深度剖析。请结合宏观背景、相关性分析等多维度视角，提供详尽的逻辑推导。")
        
        return "\n".join(prompt_parts)

    def _validate_and_fix_prediction(self, result: dict, context: dict) -> dict:
        """
        防御性校验: 修正AI可能的低级逻辑错误 (幻觉)
        
        Checklist:
        1. 做多时: SL < Entry < TP
        2. 做空时: TP < Entry < SL
        3. 入场区间: Low < High
        """
        try:
            # 1. 提取基础数据
            p = result.get("prediction", "").lower()
            current_price = context.get("current_price", 0)
            
            # 2. 获取并修正入场区间 (逻辑基础)
            entry_zone = result.get("entry_zone", {})
            if not entry_zone:
                 entry_zone = {"low": current_price, "high": current_price}
            
            entry_low = float(entry_zone.get("low", current_price))
            entry_high = float(entry_zone.get("high", current_price))
            if entry_low > entry_high: entry_low, entry_high = entry_high, entry_low
            avg_entry = (entry_low + entry_high) / 2
            
            # --- 方向一致性硬校验 (最高优先级) ---
            # 如果 AI 说的方向与给出的 TP/SL 逻辑冲突，以价位为准
            tps = [float(x) for x in result.get("take_profit", [])]
            sl = float(result.get("stop_loss", 0))
            
            is_long = False
            is_short = False
            
            # 如果有完整的止盈目标，通过止盈位判定真实方向
            is_price_long = False
            is_price_short = False
            if tps and tps[0] != avg_entry:
                if tps[0] > avg_entry:
                    is_price_long = True
                else:
                    is_price_short = True
            
            # 文本识别
            is_text_long = any(x in p for x in ["涨", "多", "bull", "buy", "long"]) and not any(x in p for x in ["不看涨", "not bull"])
            is_text_short = any(x in p for x in ["跌", "空", "bear", "sell", "short"]) and not any(x in p for x in ["不看跌", "not bear"])

            # --- 冲突判定 ---
            is_long = is_price_long
            is_short = is_price_short
            
            # 如果价位无法判断，则采用文本
            if not is_long and not is_short:
                is_long = is_text_long
                is_short = is_text_short
            # 如果价位与文本方向相反，且价位有效，则视为冲突降级
            elif (is_price_long and is_text_short) or (is_price_short and is_text_long):
                logger.warning(f"检测到方向冲突: 文本({p}) 与 价位(TP:{tps[0]}) 矛盾，降级为震荡")
                is_long = is_short = False
                # BUG-5 修复: 降级时同步更新 reasoning 和 risk_warning
                if "reasoning" not in result or not isinstance(result.get("reasoning"), list):
                    result["reasoning"] = []
                result["reasoning"].insert(0, f"⚠️ 系统检测到方向冲突: AI文本判断与价位逻辑矛盾(文本:{p}, TP:{tps[0]})，已自动降级为震荡/观望。")
                if "risk_warning" not in result or not isinstance(result.get("risk_warning"), list):
                    result["risk_warning"] = []
                result["risk_warning"].insert(0, "方向冲突已触发自动降级，建议观望等待信号明确")

            # 更新结果标签，确保前后端一致
            if is_long: 
                result["prediction"] = "看涨"
                logger.debug(f"最终方向判定: 看涨 [基于{'价位' if is_price_long else '文本'}]")
            elif is_short: 
                result["prediction"] = "看跌"
                logger.debug(f"最终方向判定: 看跌 [基于{'价位' if is_price_short else '文本'}]")
            else: 
                result["prediction"] = "震荡"
            
            # --- Anti-Chasing Logic (Smart Entry) ---
            # 防止追涨杀跌: 强制要求入场位不劣于现价太多
            if is_long:
                # 做多: 入场不能显著高于现价 (允许 0.05% 的滑点/突破确认，但不能由着AI乱来)
                limit_price = current_price * 1.0005
                if entry_high > limit_price:
                    logger.warning(f"防追涨修正(Long): Entry High({entry_high}) > Current({current_price}), 强制下调")
                    entry_high = current_price
                    # 如果区间被压扁了，把 low 也拉下来
                    if entry_low > entry_high:
                        entry_low = entry_high * 0.995 # 给 0.5% 区间

            elif is_short:
                 # 做空: 入场不能显著低于现价
                limit_price = current_price * 0.9995
                if entry_low < limit_price:
                    logger.warning(f"防追跌修正(Short): Entry Low({entry_low}) < Current({current_price}), 强制上调")
                    entry_low = current_price
                    # 如果区间被压扁了，把 high 也拉上去
                    if entry_high < entry_low:
                        entry_high = entry_low * 1.005 # 给 0.5% 区间

            # 更新回 result 价位，并确认为标准格式
            result["entry_zone"] = {"low": entry_low, "high": entry_high}
            result["stop_loss"] = sl
            result["take_profit"] = tps
            
            if not is_long and not is_short:
                  return result # 震荡/观望仅做基础校验后返回

            avg_entry = (entry_low + entry_high) / 2
            sl = float(result.get("stop_loss", 0))
            tps = [float(x) for x in result.get("take_profit", [])]
            
            if not tps:
                tps = [avg_entry * 1.02] if is_long else [avg_entry * 0.98] # 默认TP
            
            # 3. 逻辑修正
            if is_long:
                # 做多逻辑: SL < Entry
                # 尝试结合 ATR 设定更科学的 SL (如果没有给出，默认 1.5x ATR)
                atr = context.get("atr", 0)
                if sl >= entry_low:
                    logger.warning(f"逻辑修正(Long): SL({sl}) >= Entry({entry_low}), 自动下调SL")
                    if atr > 0:
                        sl = entry_low - (atr * 1.5)
                    else:
                        sl = entry_low * 0.98 # 自动设为入场下方2%
                    result["stop_loss"] = sl
                    
                # 做多逻辑: TP > Entry
                valid_tps = [tp for tp in tps if tp > entry_high]
                if not valid_tps:
                    logger.warning("逻辑修正(Long): 所有TP均低于Entry, 自动上调TP")
                    result["take_profit"] = [avg_entry * 1.02, avg_entry * 1.04, avg_entry * 1.06]
                else:
                    result["take_profit"] = valid_tps
                    
            elif is_short:
                # 做空逻辑: SL > Entry
                atr = context.get("atr", 0)
                if sl <= entry_high:
                    logger.warning(f"逻辑修正(Short): SL({sl}) <= Entry({entry_high}), 自动上调SL")
                    if atr > 0:
                        sl = entry_high + (atr * 1.5)
                    else:
                        sl = entry_high * 1.02 # 自动设为入场上方2%
                    result["stop_loss"] = sl
                    
                # 做空逻辑: TP < Entry
                valid_tps = [tp for tp in tps if tp < entry_low]
                if not valid_tps:
                    logger.warning("逻辑修正(Short): 所有TP均高于Entry, 自动下调TP")
                    result["take_profit"] = [avg_entry * 0.98, avg_entry * 0.96, avg_entry * 0.94]
                else:
                    result["take_profit"] = valid_tps

            # ========== V2.0 Pro: 1:1 减仓协议与 TP1 强制校验 ==========
            sl = float(result.get("stop_loss", 0))
            avg_entry = (entry_low + entry_high) / 2
            risk_dist = abs(avg_entry - sl)
            
            if risk_dist > 0:
                # 强制设置 TP1 为 1:1 盈亏比位置 (保本协议)
                tp1_target = avg_entry + risk_dist if is_long else avg_entry - risk_dist
                
                # 如果 AI 给出的 TP1 离 1:1 太远，强制修正
                if not tps:
                    tps = [tp1_target, tp1_target + risk_dist * 0.5, tp1_target + risk_dist * 1.5]
                else:
                    # 确保第一目标是 1:1
                    tps[0] = tp1_target
                result["take_profit"] = tps

            # --- RRR (Risk:Reward Ratio) Check (V2.0 Pro: Total RRR >= 1.5) ---
            try:
                final_tp = result["take_profit"][-1]
                reward = abs(final_tp - avg_entry)
                
                if risk_dist > 0:
                    rrr = reward / risk_dist
                    if rrr < 1.5:
                        logger.warning(f"最终RRR过低({rrr:.2f} < 1.5), 尝试上调末尾止盈或降级")
                        if rrr < 1.0:
                            result["prediction"] = "震荡"
                            result["reasoning"].insert(0, f"⚠️ 严重风险: 总盈亏比({rrr:.2f})不足1.0，策略无效，已自动降级。")
                            return result
                        else:
                            # 尝试微调 TP 以符合 1.5
                            if is_long: result["take_profit"][-1] = avg_entry + risk_dist * 1.6
                            else: result["take_profit"][-1] = avg_entry - risk_dist * 1.6
                            result["reasoning"].insert(0, f"💡 策略优化: 已自动调整止盈位以确保收益风险比 > 1.5。")
            except Exception as e:
                logger.error(f"RRR计算错误: {e}")

            # ========== V2.0 Pro: VPVR 真空区止损避雷 ==========
            vpvr = context.get("vpvr", {})
            lvn = vpvr.get("vacuum_lvn")
            poc = vpvr.get("poc_hvn")
            if lvn and sl:
                # 如果止损位落在真空区附近 (±0.5% ATR)，则认为不安全
                atr = context.get("atr", 0) or (avg_entry * 0.01)
                if abs(sl - lvn) < atr * 0.5:
                    logger.warning(f"止损碰撞真空区(LVN:{lvn}), 触发防扫损修正")
                    # 将止损向 POC 或 远离真空区的方向移动
                    if is_long:
                        sl = min(sl, lvn) - atr * 0.5 # 向下移离真空区
                    else:
                        sl = max(sl, lvn) + atr * 0.5 # 向上移离真空区
                    result["stop_loss"] = sl
                    result["reasoning"].append(f"🛡️ 止损保护: 检测到原止损点处于成交真空区(LVN)，已自动修正以防瞬间扫损。")

            # ========== V2.0 Pro: SMC 机构锚定提示 ==========
            obs = context.get("smc", {}).get("order_blocks", [])
            for ob in obs:
                # 如果入场区间触碰了 OB
                if (ob["type"] == "bullish" and is_long) or (ob["type"] == "bearish" and is_short):
                    if entry_low <= ob["top"] and entry_high >= ob["bottom"]:
                        result["summary"] = f"🎯 [SMC锚定] {result.get('summary', '')} (入场区域与机构订单块重合)"
                        break

            # 4. 时效性检查: 如果当前价格已经突破了 TP1
            tps_final = result.get("take_profit", [])
            if tps_final:
                tp1 = float(tps_final[0])
                if is_long and current_price >= tp1:
                    result["reasoning"].insert(0, f"⚠️ 提示: 现价 ({current_price}) 已触及或突破目标 TP1 ({tp1})，建议等待回调入场。")
                elif is_short and current_price <= tp1:
                    result["reasoning"].insert(0, f"⚠️ 提示: 现价 ({current_price}) 已触及或突破目标 TP1 ({tp1})，建议等待反弹入场。")

            # ========== 增强: TP距离合理性检查 (幻觉检测) ==========
            atr = context.get("atr", 0)
            if atr > 0 and tps_final:
                for i, tp in enumerate(tps_final):
                    tp_distance = abs(float(tp) - avg_entry)
                    if tp_distance > atr * 5:
                        logger.warning(f"幻觉修正: TP{i+1}({tp}) 距离入场位过远 ({tp_distance/atr:.1f}x ATR), 限制为 3x ATR")
                        if is_long:
                            tps_final[i] = avg_entry + atr * 3 * (i + 1)
                        else:
                            tps_final[i] = avg_entry - atr * 3 * (i + 1)
                result["take_profit"] = tps_final
            
            # ========== 增强: 入场区间宽度检查 ==========
            entry_width = abs(entry_high - entry_low)
            if atr > 0 and entry_width > atr * 2:
                logger.warning(f"幻觉修正: 入场区间过宽 ({entry_width:.2f} > 2*ATR={atr*2:.2f}), 收窄至 0.5*ATR")
                mid_entry = (entry_low + entry_high) / 2
                result["entry_zone"] = {
                    "low": mid_entry - atr * 0.25,
                    "high": mid_entry + atr * 0.25
                }

            # ========== 增强: 置信度上下文自动校验 (P4 加严) ==========
            confidence = result.get("confidence", 50)
            conflicts = context.get("signal_conflicts", [])
            if "risk_warning" not in result or not isinstance(result.get("risk_warning"), list):
                result["risk_warning"] = []
            if conflicts and len(conflicts) >= 3 and confidence > 60:
                old_conf = confidence
                confidence = min(confidence, 60)
                result["confidence"] = confidence
                logger.warning(f"置信度校正: {old_conf}% -> {confidence}% (存在{len(conflicts)}个信号冲突)")
                result["risk_warning"].append(f"指标信号冲突较多({len(conflicts)}个), 置信度已自动降至{confidence}%")
            elif conflicts and len(conflicts) >= 2 and confidence > 70:
                old_conf = confidence
                confidence = min(confidence, 70)
                result["confidence"] = confidence
                logger.warning(f"置信度校正: {old_conf}% -> {confidence}% (存在{len(conflicts)}个信号冲突)")
                result["risk_warning"].append(f"存在{len(conflicts)}个信号冲突, 置信度已降至{confidence}%")
            elif conflicts and len(conflicts) >= 1 and confidence > 85:
                old_conf = confidence
                confidence = min(confidence, 80)
                result["confidence"] = confidence
                logger.warning(f"置信度校正: {old_conf}% -> {confidence}% (存在{len(conflicts)}个信号冲突)")

            # ========== BUG-2/BUG-4: key_levels 校验与锚定 ==========
            result = self._validate_key_levels(result, context)

            # ========== BUG-1: reasoning 文本逻辑校验 ==========
            result = self._sanitize_reasoning(result, context)

            return result
            
        except Exception as e:
            logger.error(f"逻辑校验发生错误: {e}, 返回原始结果")
            return result

    def _validate_key_levels(self, result: dict, context: dict) -> dict:
        """
        校验 key_levels 合理性 (BUG-2 + BUG-4)
        
        1. 强制覆盖 current_price 为真实值
        2. 确保 support < current_price < resistance
        3. 如有 pivot_points，用 Pivot 锚定
        """
        try:
            current_price = context.get("current_price", 0)
            if not current_price:
                return result

            kl = result.get("key_levels", {})
            if not isinstance(kl, dict):
                kl = {}

            # BUG-4: 强制覆盖 current_price
            kl["current_price"] = current_price

            # BUG-2: 确保 support < current_price < resistance
            strong_support = float(kl.get("strong_support", 0))
            strong_resistance = float(kl.get("strong_resistance", 0))
            weak_support = float(kl.get("weak_support", 0))
            weak_resistance = float(kl.get("weak_resistance", 0))

            # 修正: 支撑位不能高于当前价
            if strong_support > 0 and strong_support >= current_price:
                logger.warning(f"key_levels修正: strong_support({strong_support}) >= 当前价({current_price}), 自动下调")
                kl["strong_support"] = current_price * 0.95
            if weak_support > 0 and weak_support >= current_price:
                logger.warning(f"key_levels修正: weak_support({weak_support}) >= 当前价({current_price}), 自动下调")
                kl["weak_support"] = current_price * 0.98

            # 修正: 阻力位不能低于当前价
            if strong_resistance > 0 and strong_resistance <= current_price:
                logger.warning(f"key_levels修正: strong_resistance({strong_resistance}) <= 当前价({current_price}), 自动上调")
                kl["strong_resistance"] = current_price * 1.05
            if weak_resistance > 0 and weak_resistance <= current_price:
                logger.warning(f"key_levels修正: weak_resistance({weak_resistance}) <= 当前价({current_price}), 自动上调")
                kl["weak_resistance"] = current_price * 1.02

            # 如有 pivot_points，做交叉验证
            pivot = context.get("pivot_points", {})
            if pivot:
                classic = pivot.get("classic", {})
                pivot_s1 = classic.get("s1")
                pivot_r1 = classic.get("r1")
                if pivot_s1 and strong_support > 0:
                    # 如果 AI 给的支撑与 Pivot S1 偏差超过 5%，发出警告
                    deviation = abs(strong_support - pivot_s1) / current_price
                    if deviation > 0.05:
                        logger.warning(f"key_levels偏差: AI support({strong_support}) vs Pivot S1({pivot_s1}), 偏差{deviation:.1%}")

            result["key_levels"] = kl

        except Exception as e:
            logger.error(f"key_levels校验错误: {e}")

        return result

    def _sanitize_reasoning(self, result: dict, context: dict) -> dict:
        """
        校验 reasoning 和 risk_warning 中的价格逻辑 (BUG-1)
        
        扫描文本中的价格引用，检测与 current_price 矛盾的表述：
        - "跌破支撑X" 但 X > current_price → 修正为 "已跌破支撑X"
        - "突破阻力X" 但 X < current_price → 修正为 "已突破阻力X"
        """
        try:
            current_price = context.get("current_price", 0)
            if not current_price:
                return result

            import re

            def fix_price_logic(text: str) -> str:
                """修正单条文本中的价格逻辑矛盾"""
                # 模式1: "向下跌破支撑X" / "跌破支撑X" 但 X > current_price
                pattern_break_support = re.compile(
                    r'(向下)?跌破(支撑|支撑位)?\s*([\d,]+\.?\d*)'
                )
                for m in pattern_break_support.finditer(text):
                    price_str = m.group(3).replace(',', '')
                    try:
                        price_val = float(price_str)
                        if price_val > current_price:
                            old = m.group(0)
                            new = f"已跌破前支撑{price_str}(当前价{current_price:.2f}已在其下方)"
                            text = text.replace(old, new)
                            logger.warning(f"reasoning修正: '{old}' → '{new}'")
                    except ValueError:
                        pass

                # 模式2: "突破阻力X" / "向上突破X" 但 X < current_price  
                pattern_break_resistance = re.compile(
                    r'(向上)?突破(阻力|阻力位)?\s*([\d,]+\.?\d*)'
                )
                for m in pattern_break_resistance.finditer(text):
                    price_str = m.group(3).replace(',', '')
                    try:
                        price_val = float(price_str)
                        if price_val < current_price:
                            old = m.group(0)
                            new = f"已突破前阻力{price_str}(当前价{current_price:.2f}已在其上方)"
                            text = text.replace(old, new)
                            logger.warning(f"reasoning修正: '{old}' → '{new}'")
                    except ValueError:
                        pass

                # 模式3: "支撑X" 但 X > current_price (支撑位应低于当前价)
                # 排除已被模式1修正过的文本 (含"前支撑"/"已跌破")
                pattern_support_above = re.compile(
                    r'(?<!前)支撑(位)?[：:]?\s*([\d,]+\.?\d*)'
                )
                for m in pattern_support_above.finditer(text):
                    price_str = m.group(2).replace(',', '')
                    try:
                        price_val = float(price_str)
                        if price_val > current_price * 1.01:  # 容忍1%误差
                            old = m.group(0)
                            new = f"前支撑位{price_str}(已失守，当前价在其下方)"
                            text = text.replace(old, new)
                            logger.warning(f"reasoning修正: 支撑位({price_val})高于当前价({current_price})")
                    except ValueError:
                        pass

                return text

            # 处理 reasoning 列表
            reasoning = result.get("reasoning", [])
            if isinstance(reasoning, list):
                result["reasoning"] = [fix_price_logic(r) for r in reasoning]

            # 处理 risk_warning 列表
            risk_warning = result.get("risk_warning", [])
            if isinstance(risk_warning, list):
                result["risk_warning"] = [fix_price_logic(r) for r in risk_warning]

        except Exception as e:
            logger.error(f"reasoning校验错误: {e}")

        return result

    def _parse_response(self, response_text: str, context_data: Optional[dict] = None) -> AnalysisResult:
        """
        解析API响应为结构化结果
        
        处理DeepSeek返回的JSON文本，转换为AnalysisResult对象。
        
        Args:
            response_text: API返回的原始文本（应为JSON格式）
            context_data: 原始上下文数据（用于校验）
        
        Returns:
            AnalysisResult: 解析后的分析结果对象
        
        Raises:
            ValueError: JSON解析失败或格式不符合预期时抛出
        """
        try:
            # 增强的JSON提取逻辑 (适配 R1/Chat 各种输出情况)
            text = response_text.strip()
            
            # [新增] 专门处理 DeepSeek R1 的 <think> 标签
            # 移除思维链内容，只保留最终 JSON
            if "<think>" in text:
                import re
                # 匹配 <think>...<think> (完整) 或 <think>... (截断)
                # re.DOTALL 让 . 匹配换行符
                text = re.sub(r"<think>.*?(?:</think>|$)", "", text, flags=re.DOTALL).strip()

            # 1. 尝试直接解析
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # 2. 尝试寻找第一个 '{' 并使用 raw_decode 解析
                start_idx = text.find('{')
                if start_idx != -1:
                    try:
                        decoder = json.JSONDecoder()
                        data, _ = decoder.raw_decode(text, start_idx)
                    except json.JSONDecodeError as e:
                        # 如果 raw_decode 失败，尝试最后的手段：手动提取最外层大括号
                        # 这主要处理 raw_decode 可能因为非标准格式失败的情况
                        logger.warning(f"raw_decode失败，尝试暴力提取: {e}")
                        
                        logger.error(f"raw_decode失败，尝试暴力提取: {e} | 响应前500字: {text[:500]}")

                        end_idx = text.rfind('}')
                        if end_idx != -1 and end_idx > start_idx:
                            sub_text = text[start_idx : end_idx + 1]
                            try:
                                data = json.loads(sub_text)
                            except:
                                # 尝试修复常见的 JSON 错误 (如同为 False, 尾部逗号)
                                # 这里可以引入更复杂的修复逻辑，或者直接报错
                                raise ValueError(f"无法解析提取的JSON片段: {e}")
                        else:
                            raise ValueError("无法找到闭合的大括号")
                else:
                    logger.error(f"响应中未找到JSON对象起始符 | 响应前500字: {text[:500]}")
                    raise ValueError("响应中未找到JSON对象起始符 '{'")
            
            # 补齐可能缺失的字段 (Pydantic 校验要求)
            if "analysis_time" not in data:
                data["analysis_time"] = datetime.now().isoformat()
            if "timeframe" not in data and context_data:
                data["timeframe"] = context_data.get("timeframe", "4h")
            
            # ========== 新增: 防御性逻辑校验与修正 ==========
            if context_data:
                data = self._validate_and_fix_prediction(data, context_data)
            # ============================================

            # 验证并创建结果对象
            result = AnalysisResult(**data)
            
            logger.info(
                f"分析结果解析成功 | {result.symbol} | "
                f"预测: {result.prediction} | 置信度: {result.confidence}%"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}\n原始响应: {response_text[:500]}...")
            raise ValueError(f"AI响应格式错误，无法解析为JSON: {e}")
        except Exception as e:
            logger.error(f"响应处理失败: {e}")
            raise ValueError(f"响应处理失败: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # C-3 修复: 减少重试次数(5→3)，移除 ValueError 防止 JSON 解析错误无限重试
        # 内部已有 R1→V3 降级循环(2次)，外层3次总计最多6次 API 调用
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError, EmptyResponseError, APIError))
    )
    async def analyze_market(
        self,
        symbol: str,
        context_data: dict[str, Any]
    ) -> AnalysisResult:
        """
        分析市场并生成预测
        
        核心方法：接收交易对符号和上下文数据，调用DeepSeek API进行分析，
        返回结构化的分析结果。
        
        Args:
            symbol: 交易对符号，如 "ETHUSDT", "BTCUSDT"
            context_data: 上下文数据字典，包含K线摘要、技术指标、新闻等信息
        
        Returns:
            AnalysisResult: 包含预测方向、置信度、逻辑链、风险警告等的分析结果
        
        Raises:
            APIError: DeepSeek API调用失败
            APITimeoutError: API请求超时（会自动重试3次）
            APIConnectionError: 网络连接错误（会自动重试3次）
            ValueError: 响应解析失败
            EmptyResponseError: API返回空内容（会自动重试3次）
        """
        logger.info(f"开始分析 {symbol}...")
        
        # [配置动态覆盖]
        # 1. 先确定使用的模型
        current_model = self.model
        current_system_prompt = self.system_prompt
        
        prefs = context_data.get("user_preferences", {})
        if prefs:
            if prefs.get("model"):
                current_model = prefs["model"]
                logger.info(f"使用用户指定模型: {current_model}")
            
            # CRIT-1 Fix: Initialize prefs early to ensure it's available for metadata injection later
            # This block was moved up, but the original `prefs` initialization was already there.
            # The instruction's `prefs.get("promptTemplate")` uses a different key casing.
            # Sticking to `prompt_template` for consistency with existing code.
            if prefs.get("prompt_template"):
                custom_prompt = prefs["prompt_template"]
                if len(custom_prompt) > 50: # 简单长度检查
                    current_system_prompt = custom_prompt
                    logger.info("使用用户自定义提示词模板")

        # 2. 自动降级策略循环 (R1 -> V3)
        # 如果 R1 失败 (超时/截断/解析错误)，自动降级到 V3
        active_model = current_model
        # 保存原始 System Prompt 以便降级时恢复
        base_system_prompt = current_system_prompt

        for attempt in range(2):
            try:
                # --- A. 根据模型构建 Prompt ---
                temp_system_prompt = base_system_prompt
                
                if "reasoner" in active_model:
                    # R1 模型: 使用推理专用 Prompt
                    user_prompt = self._build_reasoner_prompt(symbol, context_data)
                    # R1 复用完整中文系统提示词（除非用户自定义）
                    # 修复: 不再使用英文简化版，避免系统指令与用户提示词语言不一致
                else:
                    # V3/Chat 模型: 使用标准 Prompt
                    user_prompt = self._build_user_prompt(symbol, context_data)

                logger.debug(f"Prompt构建完成 (Attempt {attempt+1}) | 模型: {active_model} | SystemPrompt长度: {len(temp_system_prompt)}")
                
                # --- B. 计算 Max Tokens ---
                request_max_tokens = self.max_tokens
                if "reasoner" in active_model and request_max_tokens < 8000:
                    request_max_tokens = 8192
                    logger.info(f"为 R1 模型自适应调整 Max Tokens: {request_max_tokens}")

                # --- C. 调用 API ---
                response = await self.client.chat.completions.create(
                    model=active_model,
                    messages=[
                        {"role": "system", "content": temp_system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=request_max_tokens
                )
                
                # --- D. 验证响应 ---
                if not response.choices:
                    raise EmptyResponseError("API returned no choices")
                
                choice = response.choices[0]
                if not choice.message.content:
                    reason = choice.finish_reason
                    if reason == 'length':
                        raise EmptyResponseError(f"API output truncated (Max tokens reached). model={active_model}")
                    raise EmptyResponseError(f"API returned empty content (Finish Reason: {reason})")
                    
                response_text = choice.message.content
                logger.debug(f"API响应接收成功，长度: {len(response_text)} 字符")
                
                # --- E. 解析响应 ---
                result = self._parse_response(response_text, context_data)
                
                # --- F. 注入元数据 ---
                result.ai_model = active_model
                result.ai_prompt_template = "自定义模板" if prefs.get("prompt_template") else ("系统默认(R1)" if "reasoner" in active_model else "系统默认")
                
                # 注入透传上下文
                if context_data.get("trend_context"):
                    result.trend_context = context_data["trend_context"]
                if context_data.get("order_book"):
                    result.order_book_context = context_data["order_book"]
                
                return result

            except (EmptyResponseError, ValueError, APITimeoutError, APIConnectionError, APIError) as e:
                logger.warning(f"模型 {active_model} 调用失败: {e}")
                
                # 如果是 R1 且是第一次尝试，则降级
                if "reasoner" in active_model and attempt == 0:
                    logger.warning(">>> 正在自动降级到 DeepSeek-Chat (V3) 模型重试...")
                    active_model = "deepseek-chat"
                    continue
                
                # 否则抛出异常给上层处理
                raise
            
        # (其余异常处理已合并至上方循环)
    
    async def analyze_market_stream(
        self,
        symbol: str,
        context_data: dict[str, Any]
    ):
        """
        流式分析市场（异步生成器）
        
        支持流式输出分析过程，适用于前端实时展示。
        
        Args:
            symbol: 交易对符号
            context_data: 上下文数据
        
        Yields:
            str: 分析内容片段
        
        Example:
            >>> async for chunk in analyst.analyze_market_stream("ETHUSDT", context):
            ...     print(chunk, end="", flush=True)
        """
        # [配置动态覆盖]
        # 1. 先确定使用的模型
        current_model = self.model
        current_system_prompt = self.system_prompt
        
        prefs = context_data.get("user_preferences", {})
        
        if prefs:
            if prefs.get("model"):
                current_model = prefs["model"]
                logger.info(f"使用用户指定模型 (流式): {current_model}")
            
            # Sticking to `prompt_template` for consistency with existing code.
            if prefs.get("prompt_template"):
                custom_prompt = prefs["prompt_template"]
                if len(custom_prompt) > 50:
                    current_system_prompt = custom_prompt
                    logger.info("使用用户自定义提示词模板 (流式)")

        # 2. 根据模型选择 Prompt 构建器
        if "reasoner" in current_model:
            # R1 模型
            user_prompt = self._build_reasoner_prompt(symbol, context_data)
            # P1 修复: 不再覆盖为英文简化版，统一使用完整中文 SYSTEM_PROMPT
            # 与非流式 analyze_market 保持一致
        else:
            # V3/Chat 模型
            user_prompt = self._build_user_prompt(symbol, context_data)
            
        try:
            # R1 模型通常需要更长的 Token 窗口进行推理
            request_max_tokens = self.max_tokens
            if "reasoner" in current_model and request_max_tokens < 8000:
                request_max_tokens = 8192

            stream = await self.client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": current_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=request_max_tokens,
                stream=True
            )
            
            # MED-6 Fix: Accumulate full response for caching
            full_content = []
            
            async for chunk in stream:
                # CRIT-2 Fix: Check if choices exists and is not empty
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield content
                    full_content.append(content)
            
            # MED-6 Fix: Cache the complete result to avoid double-spending API credits
            if full_content:
                complete_text = "".join(full_content)
                try:
                    # Parse to ensure it's valid JSON before caching
                    result = self._parse_response(complete_text, context_data)
                    
                    # Inject config metadata same as analyze_market
                    result.ai_model = current_model
                    result.ai_prompt_template = "自定义模板" if prefs and prefs.get("prompt_template") else "系统默认"
                    
                    if context_data.get("trend_context"):
                        result.trend_context = context_data["trend_context"]
                    if context_data.get("order_book"):
                        result.order_book_context = context_data["order_book"]
                        
                    # Save to cache
                    # Fix Circular Import: Import locally
                    from app.services.cache_service import get_cached_analyzer
                    await get_cached_analyzer().cache_analysis(symbol, result)
                    logger.info(f"Stream analysis cached for {symbol}")
                except Exception as e:
                    logger.warning(f"Failed to cache stream result: {e}")
                    
        except Exception as e:
            logger.error(f"DeepSeek流式分析失败: {e}")
            yield f"\n[ERROR] 分析请求失败: {str(e)}"
            raise


# ============================================================
# 便捷工厂函数
# ============================================================

def create_analyst(api_key: Optional[str] = None) -> DeepSeekAnalyst:
    """
    创建DeepSeek分析师实例的便捷工厂函数
    
    Args:
        api_key: 可选的API密钥，不提供则从环境变量读取
    
    Returns:
        DeepSeekAnalyst: 初始化完成的分析师实例
    """
    return DeepSeekAnalyst(api_key=api_key)


# ============================================================
# 全局单例
# ============================================================

_analyst: Optional[DeepSeekAnalyst] = None


def get_analyst() -> DeepSeekAnalyst:
    """获取全局分析师单例"""
    global _analyst
    if _analyst is None:
        _analyst = create_analyst()
    return _analyst


def reset_analyst():
    """重置全局分析师单例，用于配置变更后刷新"""
    global _analyst
    _analyst = None
    logger.info("DeepSeek 分析师单例已重置")


# ============================================================
# 模块测试入口
# ============================================================

if __name__ == "__main__":
    # 简单的模块测试
    import asyncio
    
    # 模拟上下文数据
    test_context = {
        "kline_summary": """
        最近24小时ETH走势：
        - 开盘价: 2580 USDT
        - 最高价: 2695 USDT
        - 最低价: 2550 USDT
        - 当前价: 2650 USDT
        - 涨幅: +2.7%
        - 形成一个看涨吞没形态，突破前高
        """,
        "current_price": 2650,
        "funding_rate": 0.0012,
        "rsi": 58.5,
        "macd": "MACD金叉，DIF上穿DEA，柱状图由负转正",
        "ma_status": "价格站上MA20(2580)和MA50(2520)，均线多头排列",
        "news_headlines": [
            "以太坊ETF单日净流入1.5亿美元，创近期新高",
            "Vitalik发布EIP-7702提案，优化账户抽象体验",
            "链上数据显示巨鲸地址24小时增持5万ETH"
        ],
        "market_sentiment": "恐慌贪婪指数: 65 (贪婪区间)"
    }
    
    try:
        # 创建分析师实例（需要设置DEEPSEEK_API_KEY环境变量）
        analyst = create_analyst()
        
        # 执行分析
        result = analyst.analyze_market("ETHUSDT", test_context)
        
        # 打印结果
        print("\n" + "="*60)
        print("📊 分析结果")
        print("="*60)
        print(f"交易对: {result.symbol}")
        print(f"预测方向: {result.prediction}")
        print(f"置信度: {result.confidence}%")
        print(f"风险等级: {result.risk_level}")
        print(f"\n📝 分析摘要:\n{result.summary}")
        print(f"\n⚠️ 风险警告:")
        for warning in result.risk_warning:
            print(f"  • {warning}")
            
    except ValueError as e:
        print(f"配置错误: {e}")
    except Exception as e:
        print(f"分析失败: {e}")
