
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
    print("--- 5. 测试方向冲突修正逻辑 (以价位定方向) ---")
    analyst = DeepSeekAnalyst(api_key="mock")
    
    # 构造一个冲突场景: AI 文本说 Bearish，但价位是 Long
    mock_conflict = {
        "prediction": "Bearish (此时应做空...)", # 文本看跌
        "entry_zone": {"low": 1000.0, "high": 1010.0},
        "stop_loss": 950.0,
        "take_profit": [1100.0], # TP > Entry, 明显是做多
        "reasoning": ["Test"],
        "summary": "Test",
        "symbol": "ETHUSDT",
        "confidence": 90,
        "risk_level": "中"
    }
    context = {"current_price": 1050.0, "atr": 20.0}
    
    fixed = analyst._validate_and_fix_prediction(mock_conflict, context)
    print(f"修正后的预测标签: {fixed['prediction']}")
    if fixed['prediction'] == "看涨":
        print("[PASS] 成功检测到 TP > Entry 并将方向修正式为『看涨』")
    else:
        print(f"[FAIL] 方向修正失败，当前标签: {fixed['prediction']}")

    # 构造反向冲突: AI 文本说 Bullish，但价位是 Short
    mock_conflict_2 = {
        "prediction": "Bullish (突破在即...)", # 文本看涨
        "entry_zone": {"low": 1000.0, "high": 1010.0},
        "stop_loss": 1050.0,
        "take_profit": [900.0], # TP < Entry, 明显是做空
        "reasoning": ["Test"],
        "summary": "Test",
        "symbol": "ETHUSDT",
        "confidence": 90,
        "risk_level": "中"
    }
    fixed_2 = analyst._validate_and_fix_prediction(mock_conflict_2, context)
    print(f"修正后的预测标签: {fixed_2['prediction']}")
    if fixed_2['prediction'] == "看跌":
        print("[PASS] 成功检测到 TP < Entry 并将方向修正式为『看跌』")
    else:
        print(f"[FAIL] 方向修正失败，当前标签: {fixed_2['prediction']}")

if __name__ == "__main__":
    asyncio.run(test_logic())
