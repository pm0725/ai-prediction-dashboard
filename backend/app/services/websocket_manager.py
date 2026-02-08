"""
智链预测 - WebSocket 连接管理器
=============================
管理 WebSocket 客户端连接、断开与消息广播

Author: 智链预测团队
Version: 1.0.0
"""

from typing import List, Dict, Any
from fastapi import WebSocket
from loguru import logger
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # 活跃连接列表
        self.active_connections: List[WebSocket] = []
        # 订阅特定频道的连接 (后续可扩展)
        self.subscriptions: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """处理新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"新WS连接建立。当前在线: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """处理连接断开"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WS连接断开。当前在线: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """发送私有消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送WS消息失败: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """向所有连接广播消息"""
        if not self.active_connections:
            return
            
        # 序列化一次，提高效率
        # text_data = json.dumps(message) 
        
        # 复制列表防止迭代时修改
        # 并行发送消息
        tasks = []
        for connection in list(self.active_connections):
            tasks.append(self._safe_send(connection, message))
            
        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_send(self, connection: WebSocket, message: Dict[str, Any]):
        """安全发送单个消息"""
        try:
            await connection.send_json(message)
        except Exception as e:
            # logger.warning(f"广播WS消息失败: {e}") # 降低日志级别或忽略常见断开
            self.disconnect(connection)

# 全局单例
manager = ConnectionManager()
