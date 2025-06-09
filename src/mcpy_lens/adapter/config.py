"""
Configuration for the MCP adapter layer.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AdapterConfig:
    """Configuration for the MCP adapter layer."""
    
    # Concurrency settings
    max_concurrent_requests: int = 4  # Conservative default, configurable
    max_sessions: int = 100  # Maximum number of active sessions
    
    # Process management
    process_timeout: int = 300  # 5 minutes timeout for processes
    process_cleanup_interval: int = 60  # Cleanup interval in seconds
    
    # SSE settings
    sse_heartbeat_interval: int = 30  # Heartbeat interval in seconds
    sse_connection_timeout: int = 600  # 10 minutes connection timeout
    
    # Caching settings
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5 minutes TTL for cached responses
    cache_max_size: int = 1000  # Maximum number of cached items
    
    # Session management
    session_timeout: int = 3600  # 1 hour session timeout
    session_cleanup_interval: int = 300  # 5 minutes cleanup interval
    
    # Logging and monitoring
    enable_metrics: bool = True
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "AdapterConfig":
        """Create configuration from environment variables."""
        return cls(
            max_concurrent_requests=int(os.getenv("ADAPTER_MAX_CONCURRENT", "4")),
            max_sessions=int(os.getenv("ADAPTER_MAX_SESSIONS", "100")),
            process_timeout=int(os.getenv("ADAPTER_PROCESS_TIMEOUT", "300")),
            process_cleanup_interval=int(os.getenv("ADAPTER_CLEANUP_INTERVAL", "60")),
            sse_heartbeat_interval=int(os.getenv("ADAPTER_SSE_HEARTBEAT", "30")),
            sse_connection_timeout=int(os.getenv("ADAPTER_SSE_TIMEOUT", "600")),
            cache_enabled=os.getenv("ADAPTER_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl=int(os.getenv("ADAPTER_CACHE_TTL", "300")),
            cache_max_size=int(os.getenv("ADAPTER_CACHE_MAX_SIZE", "1000")),
            session_timeout=int(os.getenv("ADAPTER_SESSION_TIMEOUT", "3600")),
            session_cleanup_interval=int(os.getenv("ADAPTER_SESSION_CLEANUP", "300")),
            enable_metrics=os.getenv("ADAPTER_ENABLE_METRICS", "true").lower() == "true",
            log_level=os.getenv("ADAPTER_LOG_LEVEL", "INFO"),
        )
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if self.max_concurrent_requests <= 0:
            raise ValueError("max_concurrent_requests must be positive")
        if self.max_sessions <= 0:
            raise ValueError("max_sessions must be positive")
        if self.process_timeout <= 0:
            raise ValueError("process_timeout must be positive")
        if self.cache_ttl <= 0:
            raise ValueError("cache_ttl must be positive")
        if self.session_timeout <= 0:
            raise ValueError("session_timeout must be positive")
        return True
