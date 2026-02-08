"""
智链预测 - DeepSeek客户端单元测试
==================================
测试DeepSeekClient的核心功能
"""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

# 导入被测模块
import sys
sys.path.insert(0, '/Users/car/ai预测/backend')

from app.services.deepseek_client import (
    DeepSeekClient,
    PredictionResult,
    SYSTEM_PROMPT,
    get_deepseek_client
)


# ============================================================
# 测试数据
# ============================================================

MOCK_API_RESPONSE = {
    "prediction": "看涨",
    "confidence": 75,
    "reasoning": [
        "RSI指标显示超卖反弹",
        "MACD金叉形成",
        "价格突破MA20阻力"
    ],
    "key_levels": {
        "strong_resistance": 68000,
        "weak_resistance": 66500,
        "current_price": 65000,
        "weak_support": 63500,
        "strong_support": 62000
    },
    "suggested_action": "逢回调做多，目标位66500",
    "entry_zone": {
        "low": 64500,
        "high": 65200
    },
    "stop_loss": 63000,
    "take_profit": [66500, 68000, 70000],
    "risk_level": "中",
    "risk_warning": [
        "注意市场波动加剧",
        "关注宏观经济数据发布"
    ],
    "summary": "BTC短期看涨，建议逢低做多"
}

MOCK_CONTEXT = """
## 交易对: BTCUSDT

### 价格信息
- 当前价格: 65000.00
- 24小时涨跌: +2.35%
- 24小时成交量: 50000

### 技术指标
- RSI(14): 45.50
- MACD柱状图: +0.002500
"""


# ============================================================
# 测试用例
# ============================================================

class TestPredictionResult:
    """测试PredictionResult数据类"""
    
    def test_create_prediction_result(self):
        """测试创建预测结果对象"""
        result = PredictionResult(
            symbol="BTCUSDT",
            timeframe="4h",
            prediction="看涨",
            confidence=75,
            reasoning=["测试理由1", "测试理由2"],
            key_levels={"support": 60000, "resistance": 70000},
            suggested_action="测试建议",
            risk_level="中",
            risk_warning=["风险提示1"]
        )
        
        assert result.symbol == "BTCUSDT"
        assert result.prediction == "看涨"
        assert result.confidence == 75
        assert len(result.reasoning) == 2
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = PredictionResult(
            symbol="ETHUSDT",
            timeframe="1h",
            prediction="看跌",
            confidence=60
        )
        
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert data["symbol"] == "ETHUSDT"
        assert data["prediction"] == "看跌"
        assert "analysis_time" in data


class TestDeepSeekClient:
    """测试DeepSeekClient类"""
    
    @pytest.fixture
    def mock_client(self):
        """创建带模拟API的客户端"""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-api-key'}):
            client = DeepSeekClient(api_key='test-api-key')
            return client
    
    def test_init_without_api_key(self):
        """测试无API密钥时抛出异常"""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': ''}):
            with pytest.raises(ValueError, match="API key未配置"):
                DeepSeekClient(api_key='')
    
    def test_init_with_api_key(self):
        """测试使用API密钥初始化"""
        client = DeepSeekClient(api_key='test-key-12345')
        
        assert client.api_key == 'test-key-12345'
        assert client.model == 'deepseek-chat'
        assert client.client is not None
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, mock_client):
        """测试成功的市场分析"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(MOCK_API_RESPONSE)
        
        mock_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_client.analyze(
            symbol="BTCUSDT",
            context=MOCK_CONTEXT,
            timeframe="4h"
        )
        
        assert isinstance(result, PredictionResult)
        assert result.symbol == "BTCUSDT"
        assert result.prediction == "看涨"
        assert result.confidence == 75
        assert len(result.reasoning) == 3
        assert result.key_levels["strong_resistance"] == 68000
    
    @pytest.mark.asyncio
    async def test_analyze_json_error(self, mock_client):
        """测试JSON解析错误处理"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "这不是有效的JSON"
        
        mock_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ValueError, match="AI响应格式错误"):
            await mock_client.analyze("BTCUSDT", MOCK_CONTEXT)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_client):
        """测试健康检查成功"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "pong"
        
        mock_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_client.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_client):
        """测试健康检查失败"""
        mock_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("连接失败")
        )
        
        result = await mock_client.health_check()
        assert result is False


class TestSystemPrompt:
    """测试系统提示词"""
    
    def test_system_prompt_contains_prism(self):
        """测试系统提示词包含PRISM框架"""
        assert "PRISM" in SYSTEM_PROMPT
        assert "Price Action" in SYSTEM_PROMPT
        assert "Risk Assessment" in SYSTEM_PROMPT
        assert "Indicators" in SYSTEM_PROMPT
        assert "Sentiment" in SYSTEM_PROMPT
        assert "Macro" in SYSTEM_PROMPT
    
    def test_system_prompt_contains_json_format(self):
        """测试系统提示词包含JSON格式要求"""
        assert "json" in SYSTEM_PROMPT.lower()
        assert "prediction" in SYSTEM_PROMPT
        assert "confidence" in SYSTEM_PROMPT
        assert "reasoning" in SYSTEM_PROMPT


class TestGetDeepSeekClient:
    """测试工厂函数"""
    
    def test_get_client_singleton(self):
        """测试客户端单例模式"""
        # 重置全局实例
        import app.services.deepseek_client as module
        module._client_instance = None
        
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
            client1 = get_deepseek_client()
            client2 = get_deepseek_client()
            
            assert client1 is client2


# ============================================================
# 运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
