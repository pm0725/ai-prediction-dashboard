from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager
from loguru import logger
import asyncio

router = APIRouter(tags=["实时推送"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "message": "alive"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS连接异常: {e}")
        manager.disconnect(websocket)

@router.websocket("/ws/war-room/{symbol}")
async def war_room_websocket(websocket: WebSocket, symbol: str):
    """
    主力战情室专用实时数据推送 (高性能共享版)
    由 MarketDataManager 统一生产数据，本接口仅负责分发。
    """
    import uuid
    from app.services.market_data_manager import market_data_manager
    from fastapi.websockets import WebSocketState
    
    conn_id = str(uuid.uuid4())
    await manager.connect(websocket)
    
    # 订阅全局生产线
    await market_data_manager.subscribe(symbol, conn_id)
    logger.info(f"战情室订阅建立: {symbol} (ConnID: {conn_id})")
    
    last_timestamp = None
    
    try:
        while True:
            # 检查连接状态
            if websocket.client_state != WebSocketState.CONNECTED:
                break
                
            try:
                # 获取共享池中该币种的最新视图
                shared_data = market_data_manager.get_latest(symbol)
                
                if shared_data:
                    current_ts = shared_data.get("timestamp")
                    # 只有当数据是“新”的时候才推送 (避免重复负载)
                    if current_ts != last_timestamp:
                        await websocket.send_json({
                            "type": "war_room_update",
                            "symbol": symbol,
                            "data": shared_data,
                            "timestamp": current_ts
                        })
                        last_timestamp = current_ts
            except (WebSocketDisconnect, RuntimeError):
                break
            except Exception as e:
                logger.error(f"战情室转发失败 ({symbol}): {e}")
            
            # 高频轮询本地共享内存 (极低消耗)
            # 这里的 1s 轮询仅用于检查共享池更新情况
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"战情室 WS 链路异常 ({symbol}): {e}")
    finally:
        # 取消订阅，如果该币种无人观看，产线会自动停止
        await market_data_manager.unsubscribe(symbol, conn_id)
        manager.disconnect(websocket)
        logger.info(f"战情室订阅释放: {symbol} (ConnID: {conn_id})")
