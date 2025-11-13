#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración del Backend FastAPI.

Maneja variables de entorno, secrets y configuración de servicios externos.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    
    Usa pydantic-settings para cargar desde .env o variables de entorno.
    
    Examples:
        >>> settings = Settings()
        >>> print(settings.database_url)
        'postgresql://user:pass@localhost:5432/fba'
    """
    
    # Application
    app_name: str = "Amazon FBA AI Agent V2"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False)
    environment: str = Field(default="development")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_prefix: str = "/api/v2"
    
    # CORS Configuration
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost:5176", "http://localhost:8501"],
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./fba.db",  # SQLite para desarrollo rápido
    )
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=10)
    
    # Redis Cache
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    redis_url: Optional[str] = None
    
    # Event Bus
    event_stream_name: str = Field(default="fba_events")
    event_consumer_group: str = Field(default="fba_agents")
    
    # External APIs
    serpapi_key: str = Field(default="")
    serpapi_api_key: str = Field(default="")  # Alias para compatibilidad
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    claude_model: str = Field(default="claude-3-5-sonnet-20241022")
    
    # SMTP Configuration (for email notifications)
    smtp_server: Optional[str] = Field(default=None)
    smtp_port: Optional[int] = Field(default=None)
    smtp_email: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    email_mode: Optional[str] = Field(default="production")
    
    # JWT Authentication
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
    )
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = Field(default=60 * 24)  # 24 hours
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)  # seconds
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = "json"  # json or text
    
    # WebSocket
    ws_heartbeat_interval: int = 30  # seconds
    ws_max_connections: int = 1000
    
    # Cache TTL (seconds)
    cache_ttl_products: int = 3600  # 1 hour
    cache_ttl_analysis: int = 7200  # 2 hours
    cache_ttl_suppliers: int = 86400  # 24 hours
    
    # Agent Configuration
    agent_discovery_enabled: bool = True
    agent_analysis_enabled: bool = True
    agent_supplier_enabled: bool = True
    agent_pricing_enabled: bool = True
    agent_inventory_enabled: bool = True
    
    # Monitoring
    metrics_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    def __init__(self, **kwargs):
        """Initialize settings and compute derived values."""
        super().__init__(**kwargs)
        
        # Use serpapi_api_key if serpapi_key is empty
        if not self.serpapi_key and self.serpapi_api_key:
            self.serpapi_key = self.serpapi_api_key
        
        # Build Redis URL if not provided
        if not self.redis_url:
            password_part = f":{self.redis_password}@" if self.redis_password else ""
            self.redis_url = f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()

