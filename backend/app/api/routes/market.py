from fastapi import APIRouter, HTTPException, Query
from app.services.data_aggregator import BinanceDataFetcher, BINANCE_AVAILABLE, get_global_market_stats
import os
from typing import List, Dict, Any

router = APIRouter()

@router.get("/tickers", response_model=List[Dict[str, Any]])
async def get_tickers(symbols: str = Query(..., description="逗号分隔的交易对列表，例如: BTCUSDT,ETHUSDT")):
    """
    批量获取交易对的最新价格和24h涨跌幅
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    
    if not symbol_list:
        return []
    
    if not BINANCE_AVAILABLE:
         raise HTTPException(
             status_code=503, 
             detail=f"python-binance库未安装，无法连接Binance API"
         )

    # B-CRIT-1 修复: try/finally 确保关闭 session
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    fetcher = BinanceDataFetcher(api_key, api_secret)
    
    try:
        await fetcher.start_session()
        data = await fetcher.get_tickers(symbol_list)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await fetcher.close_session()

@router.get("/global")
async def get_global_stats():
    """
    获取全局市场数据
    """
    try:
        stats = await get_global_market_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/depth")
async def get_market_depth(symbol: str = Query(..., description="交易对，如 BTCUSDT")):
    """
    获取实时订单簿深度摘要 (轻量级接口)
    """
    if not BINANCE_AVAILABLE:
         raise HTTPException(status_code=503, detail="Binance API不可用")

    # B-CRIT-1 修复: try/finally 确保关闭 session
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    fetcher = BinanceDataFetcher(api_key, api_secret)
    
    try:
        await fetcher.start_session()
        order_book = await fetcher.get_order_book(symbol, limit=20)
        return order_book
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await fetcher.close_session()

