"""
智链预测 - 幻觉检测与预测校验单元测试
==========================================
测试 DeepSeekAnalyst._validate_and_fix_prediction 的核心校验逻辑

覆盖场景:
1. 做多方向冲突降级
2. 做空方向冲突降级
3. RRR 过低降级
4. TP 距离过远修正
5. 入场区间过宽修正
6. 置信度自动校准 (1/2/3 个冲突)
7. 防追涨杀跌 (Anti-Chasing)
8. key_levels 校验
9. reasoning 文本价格逻辑修正
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch
from app.engines.deepseek_analyst import DeepSeekAnalyst


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def analyst():
    """创建带模拟 API Key 的分析师实例"""
    with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
        return DeepSeekAnalyst(api_key='test-key')


def _base_result(prediction="看涨", entry_low=100, entry_high=102,
                 sl=95, tps=None, confidence=75):
    """构建基础预测结果"""
    return {
        "prediction": prediction,
        "entry_zone": {"low": entry_low, "high": entry_high},
        "stop_loss": sl,
        "take_profit": tps or [110, 115, 120],
        "confidence": confidence,
        "reasoning": ["测试逻辑1", "测试逻辑2", "测试逻辑3"],
        "risk_warning": ["风险提示1"],
        "key_levels": {
            "strong_resistance": 120,
            "strong_support": 90,
            "current_price": 101
        },
        "summary": "测试摘要"
    }


def _base_context(current_price=101, atr=3.0, signal_conflicts=None):
    """构建基础上下文"""
    return {
        "current_price": current_price,
        "atr": atr,
        "signal_conflicts": signal_conflicts or [],
    }


# ============================================================
# P1: 方向冲突检测
# ============================================================

class TestDirectionConflict:
    """测试方向冲突检测与降级"""

    def test_long_text_vs_short_price_conflict(self, analyst):
        """文本说看涨但 TP < Entry → 降级为震荡"""
        result = _base_result(
            prediction="看涨",
            entry_low=100, entry_high=102,
            tps=[95, 90, 85]  # TP低于入场 = 做空的价位逻辑
        )
        context = _base_context()
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["prediction"] == "震荡"
        assert any("冲突" in r for r in fixed["reasoning"])

    def test_short_text_vs_long_price_conflict(self, analyst):
        """文本说看跌但 TP > Entry → 降级为震荡"""
        result = _base_result(
            prediction="看跌",
            entry_low=100, entry_high=102,
            tps=[110, 115, 120]  # TP高于入场 = 做多的价位逻辑
        )
        context = _base_context()
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["prediction"] == "震荡"

    def test_consistent_long_direction(self, analyst):
        """一致的做多方向不应被降级"""
        result = _base_result(prediction="看涨", tps=[110, 115])
        context = _base_context()
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["prediction"] == "看涨"

    def test_consistent_short_direction(self, analyst):
        """一致的做空方向不应被降级"""
        # 入场价需在当前价附近且 RRR >= 1.2
        # Entry≈101, SL=108, TP1=90 → Risk≈7, Reward≈11, RRR≈1.57
        result = _base_result(
            prediction="看跌",
            entry_low=100.5, entry_high=101.5,
            sl=108, tps=[90, 85]
        )
        context = _base_context(current_price=101)
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["prediction"] == "看跌"


# ============================================================
# P2: RRR 校验 (门槛 1.2)
# ============================================================

class TestRRRCheck:
    """测试盈亏比校验"""

    def test_rrr_below_threshold_degrades(self, analyst):
        """RRR < 1.2 应降级为震荡"""
        # Entry≈101, SL=95, TP1=103.5 → Risk≈6, Reward≈2.5, RRR≈0.42
        result = _base_result(
            entry_low=100, entry_high=102,
            sl=95, tps=[103.5]
        )
        context = _base_context()
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["prediction"] == "震荡"
        assert any("盈亏比" in r for r in fixed["reasoning"])

    def test_rrr_above_threshold_passes(self, analyst):
        """RRR >= 1.2 不应降级"""
        # Entry≈101, SL=95, TP1=110 → Risk≈6, Reward≈9, RRR≈1.5
        result = _base_result(
            entry_low=100, entry_high=102,
            sl=95, tps=[110, 115]
        )
        context = _base_context()
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["prediction"] == "看涨"

    def test_rrr_borderline_1_2(self, analyst):
        """RRR 恰好=1.2 不应降级"""
        # Entry≈101, SL=96, TP1=107 → Risk=5, Reward=6, RRR=1.2
        result = _base_result(
            entry_low=100, entry_high=102,
            sl=96, tps=[107.0]
        )
        context = _base_context()
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        # RRR=6/5=1.2, 不小于1.2，应保持
        assert fixed["prediction"] == "看涨"


# ============================================================
# P3: TP 距离过远修正
# ============================================================

class TestTPDistanceCorrection:
    """测试 TP 距离过远的幻觉修正"""

    def test_tp_exceeds_5x_atr_corrected(self, analyst):
        """TP 距离 > 5x ATR 应被限制"""
        # ATR=3, Entry≈101, TP1=200 → 距离 99 > 5*3=15
        result = _base_result(tps=[200])
        context = _base_context(atr=3.0)
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        tp1 = fixed["take_profit"][0]
        # 应被限制到 3*ATR 范围内
        assert tp1 < 101 + 3 * 3 * 1.5  # 留一些容差

    def test_tp_within_5x_atr_unchanged(self, analyst):
        """TP 距离 <= 5x ATR 不应被修改"""
        # ATR=3, Entry≈101, TP1=110 → 距离 9 < 5*3=15
        result = _base_result(tps=[110, 115])
        context = _base_context(atr=3.0)
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["take_profit"][0] == 110


# ============================================================
# P4: 入场区间过宽修正
# ============================================================

class TestEntryZoneWidth:
    """测试入场区间宽度校验"""

    def test_entry_zone_exceeds_2x_atr_narrowed(self, analyst):
        """入场区间 > 2x ATR 应被收窄"""
        # ATR=3, 2*ATR=6, 入场区间=50
        result = _base_result(entry_low=80, entry_high=130, tps=[140, 150])
        context = _base_context(atr=3.0)
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        entry = fixed["entry_zone"]
        width = entry["high"] - entry["low"]
        assert width <= 3 * 2 + 0.1  # 收窄到 0.5*ATR 附近


# ============================================================
# P5: 置信度自动校准
# ============================================================

class TestConfidenceCalibration:
    """测试置信度自动校准"""

    def test_one_conflict_caps_at_80(self, analyst):
        """1 个冲突 + confidence>85 → 降至 80"""
        result = _base_result(confidence=90)
        context = _base_context(signal_conflicts=["RSI超买但趋势仍看涨"])
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["confidence"] <= 80

    def test_one_conflict_below_85_unchanged(self, analyst):
        """1 个冲突 + confidence<=85 → 不变"""
        result = _base_result(confidence=80)
        context = _base_context(signal_conflicts=["RSI超买但趋势仍看涨"])
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["confidence"] == 80

    def test_two_conflicts_caps_at_70(self, analyst):
        """2 个冲突 + confidence>70 → 降至 70"""
        result = _base_result(confidence=85)
        context = _base_context(signal_conflicts=[
            "RSI超买但趋势仍看涨",
            "MACD多头动能 vs EMA空头排列"
        ])
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["confidence"] <= 70

    def test_three_conflicts_caps_at_60(self, analyst):
        """3 个冲突 + confidence>60 → 降至 60"""
        result = _base_result(confidence=75)
        context = _base_context(signal_conflicts=[
            "RSI超买但趋势仍看涨",
            "MACD多头动能 vs EMA空头排列",
            "价格突破布林带上轨"
        ])
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["confidence"] <= 60

    def test_no_conflicts_unchanged(self, analyst):
        """无冲突 → 置信度不变"""
        result = _base_result(confidence=90)
        context = _base_context(signal_conflicts=[])
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["confidence"] == 90


# ============================================================
# P6: 防追涨杀跌 (Anti-Chasing)
# ============================================================

class TestAntiChasing:
    """测试防追涨杀跌逻辑"""

    def test_long_entry_above_current_corrected(self, analyst):
        """做多入场价 > 当前价 → 强制下调"""
        result = _base_result(
            prediction="看涨",
            entry_low=105, entry_high=110,  # 远高于现价101
            tps=[115, 120]
        )
        context = _base_context(current_price=101)
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["entry_zone"]["high"] <= 101 * 1.001

    def test_short_entry_below_current_corrected(self, analyst):
        """做空入场价 < 当前价 → 强制上调"""
        result = _base_result(
            prediction="看跌",
            entry_low=90, entry_high=95,  # 远低于现价101
            sl=108, tps=[85, 80]
        )
        context = _base_context(current_price=101)
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["entry_zone"]["low"] >= 101 * 0.999


# ============================================================
# P7: key_levels 校验
# ============================================================

class TestKeyLevels:
    """测试关键价位校验"""

    def test_support_above_price_corrected(self, analyst):
        """支撑位 > 当前价 → 自动下调"""
        result = _base_result()
        result["key_levels"]["strong_support"] = 120  # 高于当前价101
        context = _base_context(current_price=101)
        
        fixed = analyst._validate_key_levels(result, context)
        
        assert fixed["key_levels"]["strong_support"] < 101

    def test_resistance_below_price_corrected(self, analyst):
        """阻力位 < 当前价 → 自动上调"""
        result = _base_result()
        result["key_levels"]["strong_resistance"] = 90  # 低于当前价101
        context = _base_context(current_price=101)
        
        fixed = analyst._validate_key_levels(result, context)
        
        assert fixed["key_levels"]["strong_resistance"] > 101

    def test_current_price_always_overwritten(self, analyst):
        """current_price 始终被真实价格覆盖"""
        result = _base_result()
        result["key_levels"]["current_price"] = 999  # AI幻觉价格
        context = _base_context(current_price=101)
        
        fixed = analyst._validate_key_levels(result, context)
        
        assert fixed["key_levels"]["current_price"] == 101


# ============================================================
# P8: reasoning 文本价格逻辑修正
# ============================================================

class TestReasoningSanitize:
    """测试 reasoning 文本中的价格逻辑修正"""

    def test_broken_support_above_price_fixed(self, analyst):
        """'跌破支撑X' 但 X > 当前价 → 修正措辞"""
        result = {
            "reasoning": ["价格跌破支撑110"],
            "risk_warning": []
        }
        context = _base_context(current_price=101)
        
        fixed = analyst._sanitize_reasoning(result, context)
        
        # 110 > 101, 应被修正
        assert "已跌破" in fixed["reasoning"][0] or "前支撑" in fixed["reasoning"][0]

    def test_support_below_price_unchanged(self, analyst):
        """'支撑X' 且 X < 当前价 → 不修改"""
        result = {
            "reasoning": ["支撑位95上方企稳"],
            "risk_warning": []
        }
        context = _base_context(current_price=101)
        
        fixed = analyst._sanitize_reasoning(result, context)
        
        # 95 < 101, 不应被修改
        assert "支撑位95" in fixed["reasoning"][0]


# ============================================================
# SL 自动修正测试
# ============================================================

class TestSLAutoCorrect:
    """测试止损位自动修正"""

    def test_long_sl_above_entry_corrected(self, analyst):
        """做多时 SL >= Entry → 自动下调"""
        result = _base_result(
            prediction="看涨",
            entry_low=100, entry_high=102,
            sl=105,  # SL 高于入场
            tps=[110, 115]
        )
        context = _base_context(atr=3.0)
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["stop_loss"] < 100

    def test_short_sl_below_entry_corrected(self, analyst):
        """做空时 SL <= Entry → 自动上调"""
        result = _base_result(
            prediction="看跌",
            entry_low=100, entry_high=102,
            sl=98,  # SL 低于入场
            tps=[90, 85]
        )
        context = _base_context(atr=3.0)
        
        fixed = analyst._validate_and_fix_prediction(result, context)
        
        assert fixed["stop_loss"] > 102


# ============================================================
# 运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
