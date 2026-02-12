"""
智链预测 - 压力测试
===================
测试API并发请求处理能力

运行方式:
    cd backend
    /Users/car/ai预测/backend/venv/bin/python tests/test_stress.py
"""

import asyncio
import aiohttp
import time
import statistics
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import argparse
import sys


@dataclass
class RequestResult:
    """单个请求结果"""
    success: bool
    status_code: int
    response_time_ms: float
    error: Optional[str] = None


@dataclass
class StressTestResult:
    """压力测试结果"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    min_response_ms: float
    max_response_ms: float
    avg_response_ms: float
    p50_response_ms: float
    p95_response_ms: float
    p99_response_ms: float
    requests_per_second: float
    errors: List[str] = field(default_factory=list)


class StressTester:
    """压力测试器"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        concurrent_users: int = 10,
        requests_per_user: int = 10,
        timeout: int = 30
    ):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.requests_per_user = requests_per_user
        self.timeout = timeout
        self.results: List[RequestResult] = []
    
    async def make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        data: Optional[dict] = None
    ) -> RequestResult:
        """发送单个请求"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.perf_counter()
        
        try:
            if method == "GET":
                async with session.get(url, timeout=self.timeout) as response:
                    await response.json()
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    return RequestResult(
                        success=response.status == 200,
                        status_code=response.status,
                        response_time_ms=elapsed_ms
                    )
            else:
                async with session.post(url, json=data, timeout=self.timeout) as response:
                    await response.json()
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    return RequestResult(
                        success=response.status == 200,
                        status_code=response.status,
                        response_time_ms=elapsed_ms
                    )
                    
        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return RequestResult(
                success=False,
                status_code=0,
                response_time_ms=elapsed_ms,
                error="请求超时"
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return RequestResult(
                success=False,
                status_code=0,
                response_time_ms=elapsed_ms,
                error=str(e)
            )
    
    async def user_workflow(
        self,
        user_id: int,
        session: aiohttp.ClientSession
    ) -> List[RequestResult]:
        """模拟单个用户的请求流程"""
        results = []
        
        for i in range(self.requests_per_user):
            # 轮流测试不同的接口
            endpoints = [
                ("GET", "/api/analysis/health", None),
                ("GET", "/api/analysis/symbols", None),
                ("GET", "/api/analysis/context/BTCUSDT", None),
                ("POST", "/api/analysis/predict", {"symbol": "BTCUSDT", "timeframe": "4h"}),
            ]
            
            method, endpoint, data = endpoints[i % len(endpoints)]
            result = await self.make_request(session, method, endpoint, data)
            results.append(result)
            
            # 添加随机延迟，模拟真实用户行为
            await asyncio.sleep(0.1)
        
        return results
    
    async def run_stress_test(self) -> StressTestResult:
        """运行压力测试"""
        print(f"\n{'='*60}")
        print(f"  智链预测 - 压力测试")
        print(f"{'='*60}")
        print(f"  目标服务: {self.base_url}")
        print(f"  并发用户: {self.concurrent_users}")
        print(f"  每用户请求数: {self.requests_per_user}")
        print(f"  总请求数: {self.concurrent_users * self.requests_per_user}")
        print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 创建HTTP会话
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=self.concurrent_users * 2)
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        ) as session:
            
            # 预热 - 发送一个请求确保服务可用
            print("  预热中...")
            warmup = await self.make_request(session, "GET", "/api/prediction/health")
            if not warmup.success:
                print(f"  ❌ 预热失败: {warmup.error}")
                print("  请确保后端服务正在运行 (python main.py)")
                return None
            print(f"  ✅ 预热成功 ({warmup.response_time_ms:.0f}ms)\n")
            
            # 开始压力测试
            print("  开始压力测试...")
            start_time = time.perf_counter()
            
            # 创建所有用户任务
            tasks = [
                self.user_workflow(user_id, session)
                for user_id in range(self.concurrent_users)
            ]
            
            # 并发执行
            all_results = await asyncio.gather(*tasks)
            
            total_time = time.perf_counter() - start_time
            
            # 合并所有结果
            for user_results in all_results:
                self.results.extend(user_results)
        
        # 计算统计数据
        return self._calculate_statistics(total_time)
    
    def _calculate_statistics(self, total_time: float) -> StressTestResult:
        """计算测试统计数据"""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        response_times = [r.response_time_ms for r in self.results]
        sorted_times = sorted(response_times)
        
        # 百分位数计算
        def percentile(data, p):
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f]) if c != f else data[f]
        
        errors = list(set(r.error for r in failed if r.error))
        
        return StressTestResult(
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_time_seconds=total_time,
            min_response_ms=min(response_times) if response_times else 0,
            max_response_ms=max(response_times) if response_times else 0,
            avg_response_ms=statistics.mean(response_times) if response_times else 0,
            p50_response_ms=percentile(sorted_times, 50) if sorted_times else 0,
            p95_response_ms=percentile(sorted_times, 95) if sorted_times else 0,
            p99_response_ms=percentile(sorted_times, 99) if sorted_times else 0,
            requests_per_second=len(self.results) / total_time if total_time > 0 else 0,
            errors=errors
        )
    
    def print_report(self, result: StressTestResult):
        """打印测试报告"""
        print(f"\n{'='*60}")
        print(f"  压力测试报告")
        print(f"{'='*60}\n")
        
        # 基本统计
        print("  📊 基本统计")
        print(f"  {'─'*40}")
        print(f"  总请求数:     {result.total_requests}")
        print(f"  成功请求:     {result.successful_requests} ({result.successful_requests/result.total_requests*100:.1f}%)")
        print(f"  失败请求:     {result.failed_requests} ({result.failed_requests/result.total_requests*100:.1f}%)")
        print(f"  总耗时:       {result.total_time_seconds:.2f} 秒")
        print(f"  吞吐量:       {result.requests_per_second:.2f} 请求/秒")
        
        # 响应时间统计
        print(f"\n  ⏱️ 响应时间 (毫秒)")
        print(f"  {'─'*40}")
        print(f"  最小:    {result.min_response_ms:>10.2f} ms")
        print(f"  最大:    {result.max_response_ms:>10.2f} ms")
        print(f"  平均:    {result.avg_response_ms:>10.2f} ms")
        print(f"  P50:     {result.p50_response_ms:>10.2f} ms")
        print(f"  P95:     {result.p95_response_ms:>10.2f} ms")
        print(f"  P99:     {result.p99_response_ms:>10.2f} ms")
        
        # 性能评估
        print(f"\n  🎯 性能评估")
        print(f"  {'─'*40}")
        
        # 吞吐量评估
        rps = result.requests_per_second
        if rps >= 100:
            print(f"  吞吐量:  ✅ 优秀 ({rps:.0f} RPS)")
        elif rps >= 50:
            print(f"  吞吐量:  ⚠️ 良好 ({rps:.0f} RPS)")
        elif rps >= 20:
            print(f"  吞吐量:  ⚠️ 一般 ({rps:.0f} RPS)")
        else:
            print(f"  吞吐量:  ❌ 需优化 ({rps:.0f} RPS)")
        
        # 响应时间评估
        p95 = result.p95_response_ms
        if p95 < 100:
            print(f"  P95响应: ✅ 优秀 (<100ms)")
        elif p95 < 500:
            print(f"  P95响应: ⚠️ 良好 (<500ms)")
        elif p95 < 1000:
            print(f"  P95响应: ⚠️ 一般 (<1s)")
        else:
            print(f"  P95响应: ❌ 需优化 (>{p95:.0f}ms)")
        
        # 成功率评估
        success_rate = result.successful_requests / result.total_requests * 100
        if success_rate >= 99.9:
            print(f"  成功率:  ✅ 优秀 ({success_rate:.2f}%)")
        elif success_rate >= 99:
            print(f"  成功率:  ⚠️ 良好 ({success_rate:.2f}%)")
        elif success_rate >= 95:
            print(f"  成功率:  ⚠️ 一般 ({success_rate:.2f}%)")
        else:
            print(f"  成功率:  ❌ 需关注 ({success_rate:.2f}%)")
        
        # 错误信息
        if result.errors:
            print(f"\n  ❌ 错误类型")
            print(f"  {'─'*40}")
            for error in result.errors[:5]:
                print(f"  • {error[:60]}")
        
        print(f"\n{'='*60}")


async def run_endpoint_benchmark(base_url: str):
    """单独测试各个接口的性能"""
    print(f"\n{'='*60}")
    print(f"  接口基准测试")
    print(f"{'='*60}\n")
    
    endpoints = [
        ("GET", "/api/analysis/health", None, "健康检查"),
        ("GET", "/api/analysis/symbols", None, "交易对列表"),
        ("GET", "/api/analysis/context/BTCUSDT", None, "市场上下文"),
        ("POST", "/api/analysis/predict", {"symbol": "BTCUSDT", "timeframe": "4h"}, "AI预测"),
        ("POST", "/api/analysis/strategy/generate", {
            "symbol": "BTCUSDT",
            "prediction": "看涨",
            "confidence": 75,
            "risk_level": "中"
        }, "策略生成"),
    ]
    
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        print(f"  {'接口':<15} {'方法':<6} {'状态':<8} {'耗时':>10}")
        print(f"  {'─'*50}")
        
        for method, endpoint, data, name in endpoints:
            url = f"{base_url}{endpoint}"
            start = time.perf_counter()
            
            try:
                if method == "GET":
                    async with session.get(url) as resp:
                        await resp.json()
                        status = resp.status
                else:
                    async with session.post(url, json=data) as resp:
                        await resp.json()
                        status = resp.status
                
                elapsed = (time.perf_counter() - start) * 1000
                status_icon = "✅" if status == 200 else "⚠️"
                print(f"  {name:<15} {method:<6} {status_icon} {status:<4} {elapsed:>8.0f}ms")
                
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                print(f"  {name:<15} {method:<6} ❌ {'错误':<4} {elapsed:>8.0f}ms - {str(e)[:20]}")
    
    print()


async def main():
    parser = argparse.ArgumentParser(description="智链预测压力测试")
    parser.add_argument("--url", default="http://localhost:8000", help="API地址")
    parser.add_argument("--users", type=int, default=10, help="并发用户数")
    parser.add_argument("--requests", type=int, default=10, help="每用户请求数")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时(秒)")
    parser.add_argument("--benchmark", action="store_true", help="仅运行接口基准测试")
    
    args = parser.parse_args()
    
    # 运行接口基准测试
    if args.benchmark:
        await run_endpoint_benchmark(args.url)
        return
    
    # 先运行接口基准测试
    await run_endpoint_benchmark(args.url)
    
    # 运行压力测试
    tester = StressTester(
        base_url=args.url,
        concurrent_users=args.users,
        requests_per_user=args.requests,
        timeout=args.timeout
    )
    
    result = await tester.run_stress_test()
    
    if result:
        tester.print_report(result)


if __name__ == "__main__":
    asyncio.run(main())
