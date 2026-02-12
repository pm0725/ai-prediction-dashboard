"""
智链预测 - 缓存服务模块
=======================
提供多层缓存机制，优化AI分析性能

功能:
    - 内存缓存（带TTL）
    - 市场数据缓存
    - AI分析结果缓存
    - 缓存统计与监控
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, TypeVar, Generic, Callable
from dataclasses import dataclass, field
from functools import wraps
import hashlib
import json
from collections import OrderedDict

logger = logging.getLogger(__name__)


T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    value: T
    created_at: datetime
    expires_at: datetime
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests * 100


class TTLCache(Generic[T]):
    """带TTL的LRU缓存"""
    
    def __init__(
        self,
        maxsize: int = 100,
        ttl_seconds: int = 300,
        name: str = "default"
    ):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.name = name
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._stats = CacheStats()
        # 注意: 在单线程 asyncio 环境中不需要线程锁
        # 使用无操作上下文管理器保持接口兼容
        self._lock = self._noop_lock()

    class _NoOpLock:
        """可复用的无操作锁，在单线程 asyncio 中替代 threading.Lock 避免阻塞事件循环"""
        def __enter__(self): return self
        def __exit__(self, *args): pass

    @staticmethod
    def _noop_lock():
        """返回可复用的无操作锁实例"""
        return TTLCache._NoOpLock()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存值"""
        with self._lock:
            self._stats.total_requests += 1
            
            if key not in self._cache:
                self._stats.misses += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired:
                self._cache.pop(key)
                self._stats.misses += 1
                self._stats.evictions += 1
                return None
            
            # 更新LRU顺序
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats.hits += 1
            
            return entry.value
    
    def set(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """设置缓存值"""
        ttl = ttl_seconds or self.ttl_seconds
        
        with self._lock:
            # 检查是否需要驱逐
            if len(self._cache) >= self.maxsize:
                # 驱逐最旧的条目
                oldest_key = next(iter(self._cache))
                self._cache.pop(oldest_key)
                self._stats.evictions += 1
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=ttl)
            )
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                self._cache.pop(key)
                return True
            return False
    
    def clear(self) -> int:
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() 
                if v.is_expired
            ]
            for key in expired_keys:
                self._cache.pop(key)
                self._stats.evictions += 1
            return len(expired_keys)
    
    @property
    def stats(self) -> CacheStats:
        return self._stats
    
    @property
    def size(self) -> int:
        return len(self._cache)


class CachedAnalyzer:
    """带缓存的AI分析器"""
    
    def __init__(
        self,
        analysis_ttl_seconds: int = 300,  # 5分钟
        market_data_ttl_seconds: int = 60,  # 1分钟
        maxsize: int = 100
    ):
        # AI分析结果缓存（较长TTL）
        self.analysis_cache: TTLCache[Dict[str, Any]] = TTLCache(
            maxsize=maxsize,
            ttl_seconds=analysis_ttl_seconds,
            name="analysis"
        )
        
        # 市场数据缓存（较短TTL）
        self.market_cache: TTLCache[Dict[str, Any]] = TTLCache(
            maxsize=maxsize * 2,
            ttl_seconds=market_data_ttl_seconds,
            name="market_data"
        )
        
        # 上下文缓存
        self.context_cache: TTLCache[str] = TTLCache(
            maxsize=maxsize,
            ttl_seconds=market_data_ttl_seconds,
            name="context"
        )
        
        logger.info(f"CachedAnalyzer初始化: analysis_ttl={analysis_ttl_seconds}s, market_ttl={market_data_ttl_seconds}s")
    
    def _make_cache_key(self, symbol: str, timeframe: str, extra: Optional[str] = None) -> str:
        """生成缓存键"""
        key = f"{symbol}_{timeframe}"
        if extra:
            key += f"_{extra}"
        return key
    
    def get_cached_analysis(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的分析结果"""
        key = self._make_cache_key(symbol, timeframe)
        result = self.analysis_cache.get(key)
        
        if result:
            logger.debug(f"命中分析缓存: {key}")
        
        return result
    
    def cache_analysis(
        self,
        symbol: str,
        timeframe: str,
        result: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> None:
        """缓存分析结果"""
        key = self._make_cache_key(symbol, timeframe)
        self.analysis_cache.set(key, result, ttl_seconds)
        logger.debug(f"缓存分析结果: {key}")
    
    def get_cached_market_data(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的市场数据"""
        key = self._make_cache_key(symbol, timeframe, "market")
        return self.market_cache.get(key)
    
    def cache_market_data(
        self,
        symbol: str,
        timeframe: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> None:
        """缓存市场数据"""
        key = self._make_cache_key(symbol, timeframe, "market")
        self.market_cache.set(key, data, ttl_seconds)
    
    def get_cached_context(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[str]:
        """获取缓存的上下文"""
        key = self._make_cache_key(symbol, timeframe, "context")
        return self.context_cache.get(key)
    
    def cache_context(
        self,
        symbol: str,
        timeframe: str,
        context: str,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """缓存上下文"""
        key = self._make_cache_key(symbol, timeframe, "context")
        self.context_cache.set(key, context, ttl_seconds)
    
    def invalidate(self, symbol: str, timeframe: str) -> None:
        """使指定缓存失效"""
        keys_to_delete = [
            self._make_cache_key(symbol, timeframe),
            self._make_cache_key(symbol, timeframe, "market"),
            self._make_cache_key(symbol, timeframe, "context")
        ]
        
        for key in keys_to_delete:
            self.analysis_cache.delete(key)
            self.market_cache.delete(key)
            self.context_cache.delete(key)
        
        logger.debug(f"缓存已失效: {symbol}/{timeframe}")
    
    def clear_all(self) -> Dict[str, int]:
        """清空所有缓存"""
        return {
            "analysis": self.analysis_cache.clear(),
            "market": self.market_cache.clear(),
            "context": self.context_cache.clear()
        }
    
    def cleanup_expired(self) -> Dict[str, int]:
        """清理所有过期缓存"""
        return {
            "analysis": self.analysis_cache.cleanup_expired(),
            "market": self.market_cache.cleanup_expired(),
            "context": self.context_cache.cleanup_expired()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "analysis": {
                "size": self.analysis_cache.size,
                "hits": self.analysis_cache.stats.hits,
                "misses": self.analysis_cache.stats.misses,
                "hit_rate": f"{self.analysis_cache.stats.hit_rate:.1f}%",
                "evictions": self.analysis_cache.stats.evictions
            },
            "market": {
                "size": self.market_cache.size,
                "hits": self.market_cache.stats.hits,
                "misses": self.market_cache.stats.misses,
                "hit_rate": f"{self.market_cache.stats.hit_rate:.1f}%",
                "evictions": self.market_cache.stats.evictions
            },
            "context": {
                "size": self.context_cache.size,
                "hits": self.context_cache.stats.hits,
                "misses": self.context_cache.stats.misses,
                "hit_rate": f"{self.context_cache.stats.hit_rate:.1f}%",
                "evictions": self.context_cache.stats.evictions
            }
        }


# ============================================================
# 装饰器
# ============================================================

def cached(
    cache: TTLCache,
    key_func: Optional[Callable[..., str]] = None,
    ttl_seconds: Optional[int] = None
):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache._generate_key(*args, **kwargs)
            
            # 尝试获取缓存
            result = cache.get(key)
            if result is not None:
                return result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache.set(key, result, ttl_seconds)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache._generate_key(*args, **kwargs)
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(key, result, ttl_seconds)
            
            return result
        
        # 根据函数类型返回对应的wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ============================================================
# 全局实例
# ============================================================

_cached_analyzer: Optional[CachedAnalyzer] = None


def get_cached_analyzer() -> CachedAnalyzer:
    """获取全局缓存分析器实例"""
    global _cached_analyzer
    if _cached_analyzer is None:
        _cached_analyzer = CachedAnalyzer()
    return _cached_analyzer


# ============================================================
# 后台清理任务
# ============================================================

async def cache_cleanup_task(interval_seconds: int = 60):
    """后台缓存清理任务"""
    analyzer = get_cached_analyzer()
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            cleaned = analyzer.cleanup_expired()
            total_cleaned = sum(cleaned.values())
            
            if total_cleaned > 0:
                logger.info(f"缓存清理完成: {cleaned}")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"缓存清理任务错误: {e}")
