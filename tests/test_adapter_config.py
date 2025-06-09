"""
Unit tests for adapter configuration.
"""

import os
import pytest
from mcpy_lens.adapter.config import AdapterConfig


class TestAdapterConfig:
    """Test AdapterConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = AdapterConfig()
        
        assert config.max_concurrent_requests == 4
        assert config.max_sessions == 100
        assert config.process_timeout == 300
        assert config.process_cleanup_interval == 60
        assert config.sse_heartbeat_interval == 30
        assert config.sse_connection_timeout == 600
        assert config.cache_enabled is True
        assert config.cache_ttl == 300
        assert config.cache_max_size == 1000
        assert config.session_timeout == 3600
        assert config.session_cleanup_interval == 300
        assert config.enable_metrics is True
        assert config.log_level == "INFO"
    
    def test_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv("ADAPTER_MAX_CONCURRENT", "8")
        monkeypatch.setenv("ADAPTER_MAX_SESSIONS", "200")
        monkeypatch.setenv("ADAPTER_PROCESS_TIMEOUT", "600")
        monkeypatch.setenv("ADAPTER_CACHE_ENABLED", "false")
        monkeypatch.setenv("ADAPTER_CACHE_TTL", "600")
        monkeypatch.setenv("ADAPTER_LOG_LEVEL", "DEBUG")
        
        config = AdapterConfig.from_env()
        
        assert config.max_concurrent_requests == 8
        assert config.max_sessions == 200
        assert config.process_timeout == 600
        assert config.cache_enabled is False
        assert config.cache_ttl == 600
        assert config.log_level == "DEBUG"
    
    def test_validation_success(self):
        """Test successful validation."""
        config = AdapterConfig()
        assert config.validate() is True
    
    def test_validation_failures(self):
        """Test validation failures."""
        # Test negative max_concurrent_requests
        config = AdapterConfig(max_concurrent_requests=0)
        with pytest.raises(ValueError, match="max_concurrent_requests must be positive"):
            config.validate()
        
        # Test negative max_sessions
        config = AdapterConfig(max_sessions=-1)
        with pytest.raises(ValueError, match="max_sessions must be positive"):
            config.validate()
        
        # Test negative process_timeout
        config = AdapterConfig(process_timeout=0)
        with pytest.raises(ValueError, match="process_timeout must be positive"):
            config.validate()
        
        # Test negative cache_ttl
        config = AdapterConfig(cache_ttl=-1)
        with pytest.raises(ValueError, match="cache_ttl must be positive"):
            config.validate()
        
        # Test negative session_timeout
        config = AdapterConfig(session_timeout=0)
        with pytest.raises(ValueError, match="session_timeout must be positive"):
            config.validate()
    
    def test_env_defaults(self, monkeypatch):
        """Test that missing environment variables use defaults."""
        # Clear any existing environment variables
        env_vars = [
            "ADAPTER_MAX_CONCURRENT", "ADAPTER_MAX_SESSIONS", "ADAPTER_PROCESS_TIMEOUT",
            "ADAPTER_CLEANUP_INTERVAL", "ADAPTER_SSE_HEARTBEAT", "ADAPTER_SSE_TIMEOUT",
            "ADAPTER_CACHE_ENABLED", "ADAPTER_CACHE_TTL", "ADAPTER_CACHE_MAX_SIZE",
            "ADAPTER_SESSION_TIMEOUT", "ADAPTER_SESSION_CLEANUP", "ADAPTER_ENABLE_METRICS",
            "ADAPTER_LOG_LEVEL"
        ]
        
        for var in env_vars:
            monkeypatch.delenv(var, raising=False)
        
        config = AdapterConfig.from_env()
        default_config = AdapterConfig()
        
        # Should match default values
        assert config.max_concurrent_requests == default_config.max_concurrent_requests
        assert config.max_sessions == default_config.max_sessions
        assert config.process_timeout == default_config.process_timeout
        assert config.cache_enabled == default_config.cache_enabled
        assert config.log_level == default_config.log_level
