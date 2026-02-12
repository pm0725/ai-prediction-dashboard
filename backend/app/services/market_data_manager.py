"""
智链预测 - 市场数据生产管理器
============================
实现“生产者-消费者”模式，共享同一交易所数据的聚合结果，消除重复 API 调用。

Author: 智链预测团队
Version: 1.1.0 (High Performance)
"""

import asyncio
import time
from typing import Dict, Any, Set, Optional
from loguru import logger
from datetime import datetime

from app.services.data_aggregator import get_war_room_dashboard

class MarketDataManager:
    """
    市场数据中心管理器 (单例)
    
    职责:
    1. 追踪活跃 Symbol 的订阅情况。
    2. 为每个活跃 Symbol 维护唯一的后台数据生产任务 (3s 频率)。
    3. 维护全局共享的最新快照 (Shared State)。
    """
    def __init__(self):
        # 共享状态: {symbol: latest_data_dict}
        self._shared_state: Dict[str, Any] = {}
        # 订阅计数: {symbol: set(connection_ids)}
        self._subscribers: Dict[str, Set[str]] = {}
        # 生产任务: {symbol: task_object}
        self._tasks: Dict[str, asyncio.Task] = {}
        # 状态锁
        self._lock = asyncio.Lock()

    async def subscribe(self, symbol: str, connection_id: str):
        """订阅一个币种的数据"""
        async with self._lock:
            if symbol not in self._subscribers:
                self._subscribers[symbol] = set()
            
            self._subscribers[symbol].add(connection_id)
            logger.info(f"[MarketData] 订阅增加: {symbol} (总订阅: {len(self._subscribers[symbol])})")
            
            # 如果是第一个订阅者，启动生产任务
            if symbol not in self._tasks or self._tasks[symbol].done():
                self._tasks[symbol] = asyncio.create_task(self._production_loop(symbol))
                logger.info(f"[MarketData] 启动生产产线: {symbol}")

    async def unsubscribe(self, symbol: str, connection_id: str):
        """取消订阅"""
        async with self._lock:
            if symbol in self._subscribers and connection_id in self._subscribers[symbol]:
                self._subscribers[symbol].remove(connection_id)
                
                # 如果没人看了，停止生产任务
                if not self._subscribers[symbol]:
                    if symbol in self._tasks:
                        self._tasks[symbol].cancel()
                        del self._tasks[symbol]
                        logger.info(f"[MarketData] 停止生产产线: {symbol} (无订阅者)")
                    
                    if symbol in self._shared_state:
                        del self._shared_state[symbol]

    def get_latest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取最新的共享数据快照"""
        return self._shared_state.get(symbol)

    async def _production_loop(self, symbol: str):
        """单一币种的生产循环"""
        logger.info(f"[MarketData] 产线守护进程已就绪: {symbol}")
        try:
            while True:
                start_time = time.time()
                try:
                    # 调用聚合器执行真正的计算
                    # 注意: 这里不再受客户端并发影响，全系统每 3s 对相同币种只调一次
                    data = await get_war_room_dashboard(symbol)
                    
                    if data:
                        # 更新共享快照
                        self._shared_state[symbol] = data
                        
                        calc_time = (time.time() - start_time) * 1000
                        if calc_time > 1000:
                            logger.warning(f"[MarketData] {symbol} 计算耗时较长: {calc_time:.1f}ms")
                            
                except Exception as e:
                    logger.error(f"[MarketData] {symbol} 生产循环异常: {e}")
                
                # 等待 3 秒进行下一轮生产
                await asyncio.sleep(3)
                
        except asyncio.CancelledError:
            logger.info(f"[MarketData] {symbol} 产线任务被取消")
        except Exception as e:
            logger.error(f"[MarketData] {symbol} 产线发生致命错误: {e}")

# 全局单例
market_data_manager = MarketDataManager()
