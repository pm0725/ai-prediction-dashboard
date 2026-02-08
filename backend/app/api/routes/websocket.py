from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager
from loguru import logger

router = APIRouter(tags=["实时推送"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃，也可以接收客户端的心跳或订阅请求
            data = await websocket.receive_text()
            # 简单回显或处理指令 (暂无需复杂逻辑)
            await websocket.send_json({"type": "pong", "message": "alive"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS连接异常: {e}")
        manager.disconnect(websocket)
