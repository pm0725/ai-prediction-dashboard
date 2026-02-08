"""
智链预测 - 配置管理模块
========================
统一管理应用配置，支持环境变量和默认值
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class DeepSeekConfig(BaseSettings):
    """DeepSeek API配置"""
    api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    max_tokens: int = Field(default=4000, alias="DEEPSEEK_MAX_TOKENS")
    temperature: float = Field(default=0.7, alias="DEEPSEEK_TEMPERATURE")
    timeout: int = Field(default=60, alias="DEEPSEEK_TIMEOUT")
    max_retries: int = Field(default=3, alias="DEEPSEEK_MAX_RETRIES")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class ExchangeConfig(BaseSettings):
    """交易所配置"""
    # Binance
    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_secret: str = Field(default="", alias="BINANCE_SECRET")
    binance_testnet: bool = Field(default=True, alias="BINANCE_TESTNET")
    
    # OKX
    okx_api_key: str = Field(default="", alias="OKX_API_KEY")
    okx_secret: str = Field(default="", alias="OKX_SECRET")
    okx_passphrase: str = Field(default="", alias="OKX_PASSPHRASE")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    postgres_url: str = Field(
        default="postgresql://localhost:5432/zhilian",
        alias="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class AppConfig(BaseSettings):
    """应用配置"""
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # 服务配置
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # CORS配置
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS"
    )
    
    # 缓存配置
    cache_ttl: int = Field(default=300, alias="CACHE_TTL")  # 5分钟
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class Settings:
    """统一配置入口"""
    
    def __init__(self):
        self.deepseek = DeepSeekConfig()
        self.exchange = ExchangeConfig()
        self.database = DatabaseConfig()
        self.app = AppConfig()
    
    @property
    def is_production(self) -> bool:
        return not self.app.debug
    
    def validate(self) -> list[str]:
        """验证必要配置是否存在"""
        errors = []
        
        if not self.deepseek.api_key:
            errors.append("DEEPSEEK_API_KEY 未配置")
        
        return errors
    
    def to_dict(self) -> dict:
        """导出配置（隐藏敏感信息）"""
        return {
            "deepseek": {
                "base_url": self.deepseek.base_url,
                "model": self.deepseek.model,
                "max_tokens": self.deepseek.max_tokens,
                "api_key_configured": bool(self.deepseek.api_key)
            },
            "app": {
                "debug": self.app.debug,
                "log_level": self.app.log_level,
                "port": self.app.port
            }
        }


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 便捷访问
settings = get_settings()
