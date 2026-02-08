"""
智链预测 - 端到端数据流集成测试 (简化版)
==========================================
测试完整流程：前端请求 → 后端API → 数据获取 → AI分析 → 返回结果

运行方式:
    cd backend
    python tests/test_e2e_dataflow.py
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入应用模块
from app.core.config import settings
from app.services.data_fetcher import DataFetcher, get_data_fetcher
from app.services.analyzer import MarketAnalyzer, get_market_analyzer
from app.services.deepseek_client import get_deepseek_client


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_step(step_num, title):
    print(f"\n{'─'*40}")
    print(f"[步骤 {step_num}] {title}")
    print(f"{'─'*40}")


def print_result(name, value, status="✅"):
    print(f"  {status} {name}: {value}")


class DataFlowTester:
    """端到端数据流测试器"""
    
    def __init__(self, symbol: str = "BTCUSDT", timeframe: str = "4h"):
        self.symbol = symbol
        self.timeframe = timeframe
        self.results = {}
        self.errors = []
    
    async def test_step_1_data_fetching(self) -> bool:
        """步骤1: 数据获取测试"""
        print_step(1, "数据获取")
        
        try:
            fetcher = get_data_fetcher()
            print("  正在获取市场数据...")
            
            market_data = await fetcher.get_market_data(
                self.symbol, 
                self.timeframe, 
                kline_limit=50
            )
            
            klines = market_data.get("klines", [])
            ticker = market_data.get("ticker")
            funding = market_data.get("funding")
            
            self.results["market_data"] = market_data
            self.results["kline_count"] = len(klines)
            
            print_result("K线数据", f"{len(klines)} 根K线")
            print_result("Ticker", f"价格: {ticker.last_price if ticker else '(模拟)'}")
            print_result("资金费率", f"{funding.funding_rate * 100:.4f}%" if funding else "(无)")
            
            return len(klines) > 0
            
        except Exception as e:
            self.errors.append(f"数据获取失败: {e}")
            print(f"  ❌ 错误: {e}")
            return False
    
    async def test_step_2_technical_analysis(self) -> bool:
        """步骤2: 技术分析测试"""
        print_step(2, "技术分析")
        
        try:
            if "market_data" not in self.results:
                raise ValueError("缺少市场数据")
            
            market_data = self.results["market_data"]
            analyzer = get_market_analyzer()
            
            print("  正在计算技术指标...")
            
            analysis = analyzer.analyze_market(
                symbol=self.symbol,
                klines=market_data.get("klines", []),
                ticker=market_data.get("ticker"),
                funding=market_data.get("funding")
            )
            
            self.results["analysis"] = analysis
            indicators = analysis.indicators
            
            # RSI状态
            rsi = indicators.rsi_14
            rsi_status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性"
            print_result("RSI (14)", f"{rsi:.2f} [{rsi_status}]")
            
            # MACD
            macd_status = "多头" if indicators.macd_histogram > 0 else "空头"
            print_result("MACD柱状图", f"{indicators.macd_histogram:.6f} [{macd_status}]")
            
            # 均线
            print_result("SMA (20)", f"{indicators.sma_20:.2f}")
            print_result("SMA (50)", f"{indicators.sma_50:.2f}")
            
            # 趋势
            trend_emoji = "📈" if indicators.trend_status == "bullish" else "📉" if indicators.trend_status == "bearish" else "➡️"
            print_result("趋势", f"{indicators.trend_status} {trend_emoji}")
            
            # 关键价位
            print("\n  关键价位:")
            for level, price in analysis.key_levels.items():
                print(f"    • {level}: {price:.2f}")
            
            return True
            
        except Exception as e:
            self.errors.append(f"技术分析失败: {e}")
            print(f"  ❌ 错误: {e}")
            return False
    
    async def test_step_3_ai_context_formatting(self) -> bool:
        """步骤3: AI上下文格式化测试"""
        print_step(3, "AI上下文格式化")
        
        try:
            if "analysis" not in self.results:
                raise ValueError("缺少分析数据")
            
            analyzer = get_market_analyzer()
            analysis = self.results["analysis"]
            
            context = analyzer.format_context_for_ai(analysis)
            self.results["ai_context"] = context
            
            print(f"  上下文长度: {len(context)} 字符")
            print(f"\n  上下文预览:\n  {'-'*40}")
            preview = context[:500].replace('\n', '\n  ')
            print(f"  {preview}...")
            
            # 验证上下文内容
            checks = [
                ("包含交易对", self.symbol in context),
                ("包含价格信息", "价格" in context),
                ("包含技术指标", "RSI" in context and "MACD" in context),
            ]
            
            print(f"\n  内容检查:")
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"    {status} {check_name}")
            
            return all(c[1] for c in checks)
            
        except Exception as e:
            self.errors.append(f"上下文格式化失败: {e}")
            print(f"  ❌ 错误: {e}")
            return False
    
    async def test_step_4_ai_prediction(self) -> bool:
        """步骤4: AI预测分析测试"""
        print_step(4, "AI预测分析")
        
        try:
            if "ai_context" not in self.results:
                raise ValueError("缺少AI上下文")
            
            context = self.results["ai_context"]
            
            # 检查API配置
            if not settings.deepseek.api_key:
                print("  ⚠️ DeepSeek API未配置，使用模拟预测")
                
                mock_prediction = {
                    "symbol": self.symbol,
                    "timeframe": self.timeframe,
                    "prediction": "看涨",
                    "confidence": 68,
                    "reasoning": [
                        "RSI指标处于中性区间，未出现超买超卖",
                        "MACD柱状图为正，短期动能偏多",
                        "价格位于MA20上方，短期趋势向好"
                    ],
                    "key_levels": self.results["analysis"].key_levels,
                    "suggested_action": "建议在支撑位附近逢低做多",
                    "risk_level": "中",
                    "risk_warning": ["注意市场波动风险", "建议设置止损"],
                    "summary": f"{self.symbol}短期看涨，建议逢低布局",
                    "is_mock": True
                }
                
                self.results["prediction"] = mock_prediction
            else:
                print("  正在调用DeepSeek API...")
                client = get_deepseek_client()
                result = await client.analyze(self.symbol, context, self.timeframe)
                self.results["prediction"] = result.to_dict()
            
            # 显示预测结果
            prediction = self.results["prediction"]
            
            direction = prediction.get("prediction", "未知")
            confidence = prediction.get("confidence", 0)
            direction_emoji = "📈" if direction == "看涨" else "📉" if direction == "看跌" else "➡️"
            
            print(f"\n  预测结果: {direction_emoji} {direction} (置信度: {confidence}%)")
            
            print("\n  分析逻辑:")
            for i, reason in enumerate(prediction.get("reasoning", []), 1):
                print(f"    {i}. {reason}")
            
            print(f"\n  建议操作: {prediction.get('suggested_action', 'N/A')}")
            print(f"  风险等级: {prediction.get('risk_level', '未知')}")
            
            if prediction.get("risk_warning"):
                print("\n  ⚠️ 风险提示:")
                for warning in prediction.get("risk_warning", []):
                    print(f"    • {warning}")
            
            return True
            
        except Exception as e:
            self.errors.append(f"AI预测失败: {e}")
            print(f"  ❌ 错误: {e}")
            return False
    
    async def test_step_5_response_formatting(self) -> bool:
        """步骤5: 响应格式化测试"""
        print_step(5, "响应格式化 (模拟返回给前端)")
        
        try:
            if "prediction" not in self.results:
                raise ValueError("缺少预测结果")
            
            prediction = self.results["prediction"]
            
            api_response = {
                "status": "success",
                "data": {
                    "symbol": prediction.get("symbol"),
                    "timeframe": prediction.get("timeframe", self.timeframe),
                    "prediction": prediction.get("prediction"),
                    "confidence": prediction.get("confidence"),
                    "reasoning": prediction.get("reasoning", []),
                    "key_levels": prediction.get("key_levels", {}),
                    "suggested_action": prediction.get("suggested_action"),
                    "risk_level": prediction.get("risk_level"),
                    "risk_warning": prediction.get("risk_warning", []),
                    "summary": prediction.get("summary"),
                    "analysis_time": datetime.now().isoformat()
                },
                "meta": {
                    "is_mock": prediction.get("is_mock", False),
                    "kline_count": self.results.get("kline_count", 0)
                }
            }
            
            self.results["api_response"] = api_response
            
            json_str = json.dumps(api_response, ensure_ascii=False, indent=2)
            print(f"\n  API响应 (JSON):\n  {'-'*40}")
            for line in json_str.split('\n')[:25]:
                print(f"  {line}")
            if len(json_str.split('\n')) > 25:
                print("  ...")
            
            # 验证响应结构
            required_fields = ["status", "data"]
            data_fields = ["symbol", "prediction", "confidence"]
            
            print(f"\n  响应结构验证:")
            all_valid = True
            
            for field in required_fields:
                exists = field in api_response
                print(f"    {'✅' if exists else '❌'} {field}")
                if not exists:
                    all_valid = False
            
            for field in data_fields:
                exists = field in api_response.get("data", {})
                print(f"    {'✅' if exists else '❌'} data.{field}")
                if not exists:
                    all_valid = False
            
            return all_valid
            
        except Exception as e:
            self.errors.append(f"响应格式化失败: {e}")
            print(f"  ❌ 错误: {e}")
            return False
    
    async def run_full_test(self):
        """运行完整的端到端测试"""
        print_header("智链预测 - 端到端数据流测试")
        print(f"  交易对: {self.symbol}")
        print(f"  时间周期: {self.timeframe}")
        print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        steps = [
            ("数据获取", self.test_step_1_data_fetching),
            ("技术分析", self.test_step_2_technical_analysis),
            ("上下文格式化", self.test_step_3_ai_context_formatting),
            ("AI预测", self.test_step_4_ai_prediction),
            ("响应格式化", self.test_step_5_response_formatting),
        ]
        
        results = []
        for step_name, step_func in steps:
            try:
                success = await step_func()
                results.append((step_name, success))
            except Exception as e:
                print(f"  ❌ {step_name}步骤发生异常: {e}")
                results.append((step_name, False))
                break
        
        # 最终报告
        print_header("测试报告")
        
        passed = sum(1 for _, s in results if s)
        total = len(results)
        
        for step_name, success in results:
            status = "✅ 通过" if success else "❌ 失败"
            print(f"  {status} - {step_name}")
        
        print(f"\n  通过率: {passed}/{total} ({passed/total*100:.0f}%)")
        
        if self.errors:
            print("\n  错误列表:")
            for error in self.errors:
                print(f"    • {error}")
        
        if passed == total:
            print("\n  🎉 端到端测试全部通过！")
        elif passed >= total * 0.8:
            print("\n  ⚠️ 测试基本通过，部分功能可能受限")
        else:
            print("\n  ❌ 测试失败，请检查错误信息")
        
        return passed == total


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="智链预测端到端测试")
    parser.add_argument("--symbol", default="BTCUSDT", help="交易对")
    parser.add_argument("--timeframe", default="4h", help="时间周期")
    
    args = parser.parse_args()
    
    tester = DataFlowTester(args.symbol, args.timeframe)
    success = await tester.run_full_test()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
