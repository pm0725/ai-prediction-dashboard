
import pytest
import asyncio
from app.services.data_aggregator import get_war_room_dashboard

@pytest.mark.asyncio
async def test_war_room_dashboard_structure():
    """
    测试 War Room Dashboard 数据结构完整性
    """
    symbol = "BTCUSDT"
    print(f"\nFetching War Room data for {symbol}...")
    
    data = await get_war_room_dashboard(symbol)
    
    # 1. 验证顶层结构
    assert "symbol" in data
    assert "timestamp" in data
    assert "trend_resonance" in data
    assert "key_levels" in data
    assert "smart_money" in data
    assert "volatility" in data
    
    # 2. 验证多周期共振
    resonance = data["trend_resonance"]
    assert "summary" in resonance
    assert len(resonance["details"]) == 4 # 15m, 1h, 4h, 1d
    
    # 3. 验证关键位
    levels = data["key_levels"]
    assert "current_price" in levels
    assert "nearest_support" in levels
    assert "nearest_resistance" in levels
    assert "in_sniper_zone" in levels
    
    # 4. 验证 Smart Money
    sm = data["smart_money"]
    assert "signal" in sm
    
    # 5. 验证波动率
    vol = data["volatility"]
    assert "status" in vol
    
    print("\n✅ War Room Dashboard structure verified!")
    print(data)

if __name__ == "__main__":
    asyncio.run(test_war_room_dashboard_structure())
