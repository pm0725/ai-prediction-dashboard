
import sys
import os
import json
import asyncio
from datetime import datetime

# 将项目根目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.engines.deepseek_analyst import DeepSeekAnalyst, AnalysisResult
from backend.app.services.data_aggregator import calculate_indicators
import pandas as pd
import numpy as np

async def test_logic():
    print("--- 1. 测试 Pydantic 校验器兼容性 ---")
    # 测试各种变体是否能被正确归一化
    test_cases = ["看涨 (Bullish)", "Strong Bearish", "Neutral (RRR Low)", "震荡 (Neutral)"]
    for case in test_cases:
        try:
            # 构造完整的模拟数据
            data = {
                "symbol": "BTCUSDT",
                "prediction": case,
                "confidence": 80,
                "reasoning": ["Test"],
                "summary": "Test",
                "entry_zone": {"low": 40000.0, "high": 41000.0},
                "stop_loss": 39000.0,
                "take_profit": [45000.0],
                "risk_level": "中",
                "timestamp": datetime.now().isoformat(),
                "analysis_time": datetime.now().isoformat(),
                "key_levels": {"strong_resistance": 45000.0, "weak_resistance": 42000.0, "current_price": 40500.0, "weak_support": 39500.0, "strong_support": 38000.0},
                "suggested_action": "Wait",
                "risk_warning": ["High risk"] # 修正为列表
            }
            res = AnalysisResult(**data)
            print(f"输入: '{case}' -> 归一化结果: '{res.prediction}' [PASS]")
        except Exception as e:
            print(f"输入: '{case}' -> 失败: {e} [FAIL]")

    print("\n--- 2. 测试 RRR 降级逻辑 ---")
    analyst = DeepSeekAnalyst(api_key="mock")
    # 构造一个盈亏比极差的情况 (做多，但 TP1 低于 Entry)
    mock_result = {
        "prediction": "Bullish",
        "entry_zone": {"low": 100.0, "high": 100.0},
        "stop_loss": 90.0,
        "take_profit": [95.0], # TP1 < Entry
        "reasoning": ["Test"],
        "summary": "Test",
        "symbol": "BTCUSDT",
        "confidence": 90,
        "risk_level": "中"
    }
    context = {"current_price": 100.0, "atr": 0.0}
    fixed = analyst._validate_and_fix_prediction(mock_result, context)
    print(f"RRR修正结果: {fixed['prediction']}")
    print(f"风控提示: {fixed['reasoning'][0]}")
    if fixed['prediction'] == "震荡":
        print("[PASS] 成功降级为“震荡”并保留提示")
    else:
        print("[FAIL] 未能正确处理低盈亏比")

    print("\n--- 3. 测试 ATR 防御性止损逻辑 ---")
    mock_result_2 = {
        "prediction": "Bullish",
        "entry_zone": {"low": 100.0, "high": 100.0},
        "stop_loss": 110.0, # 错误止损 (高于入场)
        "take_profit": [120.0],
        "reasoning": ["Test"],
        "symbol": "BTCUSDT"
    }
    context_2 = {"current_price": 100.0, "atr": 2.0} # 有 ATR 数据
    fixed_2 = analyst._validate_and_fix_prediction(mock_result_2, context_2)
    print(f"ATR修正后的止损: {fixed_2['stop_loss']} (预期值: 100 - 1.5*2 = 97.0)")
    if fixed_2['stop_loss'] == 97.0:
        print("[PASS] 成功应用 ATR 动态止损修正")
    else:
        print(f"[FAIL] 止损修正值不符: {fixed_2['stop_loss']}")

    print("\n--- 4. 测试指标计算 Fallback 算法 (Wilder's Smoothing) ---")
    # 构造完整的 OHLCV 模拟数据
    data = {
        'open': [10.0]*16,
        'high': [10.0]*16, 
        'low': [10.0]*16,
        'close': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
        'volume': [1000.0]*16
    }
    df = pd.DataFrame(data)
    indicators = calculate_indicators(df)
    print(f"RSI 计算结果: {indicators.rsi_14:.2f}")
    
    # 构建波动数据测试 ATR
    data_atr = {
        'open': [100.0]*20,
        'high': [110.0]*20,
        'low': [90.0]*20,
        'close': [100.0]*20,
        'volume': [1000.0]*20
    }
    df_atr = pd.DataFrame(data_atr)
    indicators_atr = calculate_indicators(df_atr)
    print(f"ATR 计算结果: {indicators_atr.atr_14:.2f}")

    if indicators.rsi_14 > 95 and indicators_atr.atr_14 == 20.0:
        print("[PASS] 指标 Fallback 算法执行正常")
    else:
        print(f"[FAIL] 指标计算异常: RSI={indicators.rsi_14}, ATR={indicators_atr.atr_14}")

    print("\n--- 5. 测试 Prompt 完整性 (depth 门控) ---")
    # 构造包含所有上下文字段的 mock context_data
    full_context = {
        "current_price": 100.0,
        "timeframe": "4h",
        "rsi": 50,
        "macd": "0/0/0",
        "atr": 2.0,
        "volume_24h": 50000,
        "kline_summary": "测试K线摘要",
        "user_preferences": {"depth": 2, "risk": "moderate"},
        "candlestick_patterns": ["锤子线 (Hammer)"],
        "signal_conflicts": ["RSI与MACD方向矛盾"],
        "trend_lines": {"resistance_line": {"current_value": 105, "distance_pct": 5.0}},
        "fear_greed_index": {"value": 25, "classification": "恐惧"},
        "order_book": {
            "bid_ask_ratio": 1.2, "nearby_pressure": "balanced",
            "major_support": {"price": 95, "volume": 100},
            "major_resistance": {"price": 110, "volume": 80}
        },
        "volatility_score": 50,
        "whale_activity": {"whale_ratio": 0.5, "net_whale_vol": 1000},
    }

    analyst = DeepSeekAnalyst(api_key="mock")

    # depth=2: 应包含深度数据，不含高级数据
    full_context["user_preferences"]["depth"] = 2
    prompt_d2 = analyst._build_user_prompt("BTCUSDT", full_context)
    d2_checks = {
        "K线形态": "K线形态识别" in prompt_d2,
        "信号冲突": "信号冲突提醒" in prompt_d2,
        "趋势线":  "趋势线识别" in prompt_d2,
        "恐惧贪婪": "Fear & Greed" in prompt_d2,
        "订单簿":  "市场深度" in prompt_d2,
        "机构预警": "机构级大行情预警" in prompt_d2,
        "分析任务": "分析任务" in prompt_d2,
        "用户偏好": "用户偏好设置" in prompt_d2,
    }
    d2_pass = all(d2_checks.values())
    print(f"depth=2 (标准): {d2_checks}")
    print(f"[{'PASS' if d2_pass else 'FAIL'}] depth=2 深度数据注入")

    # depth=1: 不应包含深度数据 (K线形态/订单簿增强版等)，但应含机构预警
    full_context["user_preferences"]["depth"] = 1
    prompt_d1 = analyst._build_user_prompt("BTCUSDT", full_context)
    d1_checks = {
        "无K线形态": "### K线形态识别" not in prompt_d1,
        "无订单簿增强": "### 市场深度 (Order Book)" not in prompt_d1,
        "有机构预警": "机构级大行情预警" in prompt_d1,
        "有分析任务": "分析任务" in prompt_d1,
    }
    d1_pass = all(d1_checks.values())
    print(f"depth=1 (快速): {d1_checks}")
    print(f"[{'PASS' if d1_pass else 'FAIL'}] depth=1 门控生效")

    # depth=3: 应包含全部数据 (加入清算风险等高级数据的mock)
    full_context["user_preferences"]["depth"] = 3
    full_context["liquidation_levels"] = {
        "long_liq": {"50x": 98.0, "20x": 95.0},
        "short_liq": {"50x": 102.0, "20x": 105.0}
    }
    full_context["trend_context"] = {
        "trend_status": "bullish", "rsi": 60, "ema_21": 99,
        "bb_width": 0.05, "summary": "4h 上升趋势"
    }
    full_context["pivot_points"] = {
        "classic": {"p": 100, "r1": 105, "r2": 110, "s1": 95, "s2": 90},
        "fibonacci": {"p": 100, "r1": 103, "r2": 106, "s1": 97, "s2": 94}
    }
    prompt_d3 = analyst._build_user_prompt("BTCUSDT", full_context)
    d3_checks = {
        "清算风险": "清算风险" in prompt_d3,
        "趋势周期": "趋势周期背景" in prompt_d3,
        "Pivot": "关键支撑/阻力位" in prompt_d3,
    }
    d3_pass = all(d3_checks.values())
    print(f"depth=3 (深度): {d3_checks}")
    print(f"[{'PASS' if d3_pass else 'FAIL'}] depth=3 高级数据注入")

if __name__ == "__main__":
    asyncio.run(test_logic())
