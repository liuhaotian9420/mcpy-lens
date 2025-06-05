"""
Unit tests for wrapper configuration.
"""

import os
import pytest
from mcpy_lens.wrapper.config import WrapperConfig


class TestWrapperConfig:
    """Test WrapperConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = WrapperConfig()
        
        assert config.max_execution_time == 300
        assert config.max_memory_mb == 512
        assert config.max_output_lines == 10000
        assert config.max_concurrent_processes == 8
        assert config.python_executable == "python"
        assert config.working_directory is None
        assert config.stream_buffer_size == 1024
        assert config.stream_flush_interval == 0.1
        assert config.allow_network_access is True
        assert config.allow_file_write is True
    
    def test_from_env_defaults(self):
        """Test creating config from environment with defaults."""
        # Clear any existing env vars
        env_vars = [
            "WRAPPER_MAX_EXECUTION_TIME",
            "WRAPPER_MAX_MEMORY_MB", 
            "WRAPPER_MAX_OUTPUT_LINES",
            "WRAPPER_MAX_CONCURRENT",
            "WRAPPER_PYTHON_EXECUTABLE",
            "WRAPPER_WORKING_DIR",
            "WRAPPER_STREAM_BUFFER",
            "WRAPPER_STREAM_FLUSH",
            "WRAPPER_ALLOW_NETWORK",
            "WRAPPER_ALLOW_FILE_WRITE"
        ]
        
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
        
        config = WrapperConfig.from_env()
        
        # Should use defaults
        assert config.max_execution_time == 300
        assert config.python_executable == "python"
        assert config.allow_network_access is True
    
    def test_from_env_custom_values(self):
        """Test creating config from environment with custom values."""
        # Set custom environment variables
        os.environ["WRAPPER_MAX_EXECUTION_TIME"] = "600"
        os.environ["WRAPPER_MAX_MEMORY_MB"] = "1024"
        os.environ["WRAPPER_PYTHON_EXECUTABLE"] = "python3"
        os.environ["WRAPPER_ALLOW_NETWORK"] = "false"
        
        try:
            config = WrapperConfig.from_env()
            
            assert config.max_execution_time == 600
            assert config.max_memory_mb == 1024
            assert config.python_executable == "python3"
            assert config.allow_network_access is False
            
        finally:
            # Clean up
            for var in ["WRAPPER_MAX_EXECUTION_TIME", "WRAPPER_MAX_MEMORY_MB", 
                       "WRAPPER_PYTHON_EXECUTABLE", "WRAPPER_ALLOW_NETWORK"]:
                if var in os.environ:
                    del os.environ[var]
    
    def test_get_subprocess_env_default(self):
        """Test getting subprocess environment with defaults."""
        config = WrapperConfig()
        env = config.get_subprocess_env()
        
        # Should include current environment
        assert "PATH" in env or "Path" in env  # Windows uses "Path"
        
        # Should not have proxy restrictions by default
        assert "NO_PROXY" not in env
    
    def test_get_subprocess_env_no_network(self):
        """Test getting subprocess environment with network disabled."""
        config = WrapperConfig(allow_network_access=False)
        env = config.get_subprocess_env()
        
        # Should have proxy restrictions
        assert env["NO_PROXY"] == "*"
        assert env["no_proxy"] == "*"
