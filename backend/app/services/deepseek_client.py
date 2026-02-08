"""
智链预测 - DeepSeek客户端模块
=============================
封装与DeepSeek API的所有交互
"""

import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from openai import AsyncOpenAI, OpenAI
from openai import APIError, APIConnectionError, RateLimitError
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# 数据模型
# ============================================================

@dataclass
class TradingSignal:
    """交易信号"""
    type: str  # LONG/SHORT/WAIT
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[list[float]] = None
    position_size: str = "2%"
    risk_reward_ratio: Optional[float] = None


@dataclass
class ReasoningDetails:
    """分析理由详情"""
    technical: str = ""
    sentiment: str = ""
    macro: str = ""
    risk_factors: list[str] = field(default_factory=list)


@dataclass
class PredictionResult:
    """预测结果数据类"""
    symbol: str
    timeframe: str
    prediction: str  # strong_bullish/bullish/neutral/bearish/strong_bearish
    prediction_cn: str = ""  # 中文预测
    confidence: int = 50  # 0-100
    
    # 关键价位
    key_levels: Dict[str, Any] = field(default_factory=dict)
    
    # 交易信号
    trading_signals: list[TradingSignal] = field(default_factory=list)
    
    # 分析理由
    reasoning: ReasoningDetails = field(default_factory=ReasoningDetails)
    
    # 市场状态
    market_phase: str = "consolidating"  # trending/consolidating/reversing
    volatility_level: str = "medium"  # low/medium/high/extreme
    
    # 摘要
    summary: str = ""
    
    # 元数据
    analysis_time: str = field(default_factory=lambda: datetime.now().isoformat())
    raw_response: Optional[str] = None
    
    # 兼容旧格式的字段
    suggested_action: str = ""
    entry_zone: Optional[Dict[str, float]] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[list[float]] = None
    risk_level: str = "中"
    risk_warning: list[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 转换trading_signals
        signals = []
        for sig in self.trading_signals:
            signals.append({
                "type": sig.type,
                "entry": sig.entry,
                "stop_loss": sig.stop_loss,
                "take_profit": sig.take_profit,
                "position_size": sig.position_size,
                "risk_reward_ratio": sig.risk_reward_ratio
            })
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "prediction": self.prediction,
            "prediction_cn": self.prediction_cn,
            "confidence": self.confidence,
            "key_levels": self.key_levels,
            "trading_signals": signals,
            "reasoning": {
                "technical": self.reasoning.technical,
                "sentiment": self.reasoning.sentiment,
                "macro": self.reasoning.macro,
                "risk_factors": self.reasoning.risk_factors
            },
            "market_phase": self.market_phase,
            "volatility_level": self.volatility_level,
            "summary": self.summary,
            "analysis_time": self.analysis_time,
            # 兼容旧格式
            "suggested_action": self.suggested_action,
            "risk_level": self.risk_level,
            "risk_warning": self.risk_warning
        }


# ============================================================
# 系统提示词
# ============================================================

SYSTEM_PROMPT = """你是一位有15年经验的加密货币量化交易总监，擅长识别市场微观结构变化和风险管理。

## 分析框架

### 1. 宏观与微观共振分析
- **多周期共振**: 必须结合 `trend_context` (大级别趋势) 和当前周期走势。只有当大周期趋势（如日线）与当前周期（如4h）方向一致时，才可给予高置信度。
- **逆势交易警惕**: 若当前信号与大周期趋势相反，必须提示风险并降低仓位。

### 2. 关键价位与盘口形态
- **订单簿分析**: 利用 `order_book` 中的买卖墙 (Wall) 识别强支撑/压力。如果上方有巨量卖单压制，应谨慎看涨。
- **支撑/阻力**: 结合K线密集区和订单簿堆积区确认关键位。

### 3. 技术指标分析
- RSI: 关注超买超卖及背离信号。
- MACD: 确认动能强弱。
- 均线系统: 评估长期趋势方向。

### 4. 市场情绪与资金面
- **多空博弈**: 关注 `long_short_ratio` (多空比) 和 `funding_rate` (资金费率)。
- **反向指标**: 若散户多头极度拥挤且费率极高，往往是反向做空信号。

### 5. 事件影响评估 (如有)
- 宏观经济事件
- 项目新闻动态

## 输出要求

你必须严格按照以下JSON格式输出，不要有任何其他文字：

```json
{
  "prediction": "strong_bullish|bullish|neutral|bearish|strong_bearish",
  "prediction_cn": "强烈看涨|看涨|震荡|看跌|强烈看跌",
  "confidence": 0-100的整数,
  "timeframe": "1h|4h|1d",
  "key_levels": {
    "supports": [支撑位数组],
    "resistances": [阻力位数组],
    "current_price": 当前价格
  },
  "trading_signals": [
    {
      "type": "LONG|SHORT|WAIT",
      "entry": 入场价格,
      "stop_loss": 止损价格,
      "take_profit": [止盈价格数组],
      "position_size": "1-5%",
      "risk_reward_ratio": 盈亏比数值
    }
  ],
  "reasoning": {
    "technical": "技术分析核心理由",
    "sentiment": "情绪面分析理由",
    "macro": "宏观层面影响",
    "risk_factors": ["风险因素1", "风险因素2"]
  },
  "market_phase": "trending|consolidating|reversing",
  "volatility_level": "low|medium|high|extreme",
  "summary": "一句话总结当前市场状态和建议"
}
```

## 重要规则

1. **风险优先**: 永远优先考虑风险管理，止损必须明确
2. **概率思维**: 避免使用绝对化语言（"一定"、"肯定"、"必然"）
3. **不确定处理**: 信息不明确时降低置信度并建议观望(WAIT)
4. **成本意识**: 考虑交易成本（手续费约0.1%、滑点约0.05%）
5. **盈亏比要求**: 推荐的交易盈亏比至少1.5:1
6. **仓位控制**: 单笔交易仓位建议不超过总资金5%"""



# ============================================================
# DeepSeek客户端
# ============================================================

class DeepSeekClient:
    """DeepSeek API客户端（异步版本）"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.deepseek.api_key
        self.base_url = base_url or settings.deepseek.base_url
        self.model = model or settings.deepseek.model
        self.max_tokens = settings.deepseek.max_tokens
        self.temperature = settings.deepseek.temperature
        self.timeout = settings.deepseek.timeout
        self.max_retries = settings.deepseek.max_retries
        
        # 验证API密钥
        if not self.api_key:
            raise ValueError("DeepSeek API key未配置，请设置DEEPSEEK_API_KEY环境变量")
        
        # 初始化异步客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            max_retries=self.max_retries
        )
        
        # 同步客户端（用于非异步场景）
        self._sync_client: Optional[OpenAI] = None
    
    @property
    def sync_client(self) -> OpenAI:
        """获取同步客户端"""
        if self._sync_client is None:
            self._sync_client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                max_retries=self.max_retries
            )
        return self._sync_client
    
    async def analyze(
        self,
        symbol: str,
        context: str,
        timeframe: str = "4h"
    ) -> PredictionResult:
        """
        执行AI预测分析
        
        Args:
            symbol: 交易对符号
            context: 市场上下文数据
            timeframe: 分析周期
            
        Returns:
            PredictionResult: 预测结果
        """
        user_prompt = f"""请分析 {symbol} 在 {timeframe} 周期的后市走势。

## 市场数据

{context}

请基于以上数据，使用分析框架进行全面分析，并严格按照JSON格式输出预测结果。"""

        try:
            logger.info(f"开始分析 {symbol} ({timeframe})")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.debug(f"AI响应: {content[:200]}...")
            
            # 解析JSON
            result_dict = json.loads(content)
            
            # 解析reasoning
            reasoning_data = result_dict.get("reasoning", {})
            if isinstance(reasoning_data, dict):
                reasoning = ReasoningDetails(
                    technical=reasoning_data.get("technical", ""),
                    sentiment=reasoning_data.get("sentiment", ""),
                    macro=reasoning_data.get("macro", ""),
                    risk_factors=reasoning_data.get("risk_factors", [])
                )
            else:
                # 兼容旧格式（列表）
                reasoning = ReasoningDetails(
                    technical="; ".join(reasoning_data) if isinstance(reasoning_data, list) else "",
                    risk_factors=[]
                )
            
            # 解析trading_signals
            signals_data = result_dict.get("trading_signals", [])
            trading_signals = []
            for sig in signals_data:
                if isinstance(sig, dict):
                    trading_signals.append(TradingSignal(
                        type=sig.get("type", "WAIT"),
                        entry=sig.get("entry"),
                        stop_loss=sig.get("stop_loss"),
                        take_profit=sig.get("take_profit"),
                        position_size=sig.get("position_size", "2%"),
                        risk_reward_ratio=sig.get("risk_reward_ratio")
                    ))
            
            # 构建结果对象
            result = PredictionResult(
                symbol=symbol,
                timeframe=timeframe,
                prediction=result_dict.get("prediction", "neutral"),
                prediction_cn=result_dict.get("prediction_cn", "震荡"),
                confidence=result_dict.get("confidence", 50),
                key_levels=result_dict.get("key_levels", {}),
                trading_signals=trading_signals,
                reasoning=reasoning,
                market_phase=result_dict.get("market_phase", "consolidating"),
                volatility_level=result_dict.get("volatility_level", "medium"),
                summary=result_dict.get("summary", ""),
                raw_response=content,
                # 兼容字段
                risk_level=result_dict.get("risk_level", "中"),
                risk_warning=reasoning.risk_factors if reasoning.risk_factors else []
            )
            
            logger.info(f"分析完成: {symbol} -> {result.prediction} (置信度: {result.confidence}%)")
            return result

            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise ValueError(f"AI响应格式错误: {e}")
        except APIConnectionError as e:
            logger.error(f"API连接失败: {e}")
            raise ConnectionError(f"无法连接DeepSeek API: {e}")
        except RateLimitError as e:
            logger.error(f"API速率限制: {e}")
            raise Exception(f"API调用频率过高，请稍后重试")
        except APIError as e:
            logger.error(f"API错误: {e}")
            raise Exception(f"DeepSeek API错误: {e}")
    
    async def analyze_stream(
        self,
        symbol: str,
        context: str,
        timeframe: str = "4h"
    ) -> AsyncGenerator[str, None]:
        """
        流式分析（用于实时展示分析过程）
        
        Yields:
            str: 分析过程的文本片段
        """
        user_prompt = f"""请分析 {symbol} 在 {timeframe} 周期的后市走势。

## 市场数据

{context}

请详细阐述你的分析过程，最后给出结论。"""

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"流式分析失败: {e}")
            yield f"\n\n[错误] 分析过程中断: {str(e)}"
    
    def analyze_sync(
        self,
        symbol: str,
        context: str,
        timeframe: str = "4h"
    ) -> PredictionResult:
        """同步版本的分析方法"""
        return asyncio.run(self.analyze(symbol, context, timeframe))
    
    async def health_check(self) -> bool:
        """检查API连接状态"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False


# ============================================================
# 工厂函数
# ============================================================

_client_instance: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    """获取DeepSeek客户端单例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = DeepSeekClient()
    return _client_instance


async def get_async_client() -> DeepSeekClient:
    """异步获取客户端（用于FastAPI依赖注入）"""
    return get_deepseek_client()
