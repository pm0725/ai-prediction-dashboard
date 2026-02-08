# API路由模块
from .analysis import router as analysis_router
from .prediction import router as prediction_router
from .market import router as market_router

__all__ = ["analysis_router", "prediction_router", "market_router"]
