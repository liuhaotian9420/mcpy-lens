"""
Configuration for wrapper execution with global resource limits.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class WrapperConfig:
    """Global configuration for wrapper execution."""
    
    # Resource limits
    max_execution_time: int = 300  # 5 minutes
    max_memory_mb: int = 512  # 512 MB
    max_output_lines: int = 10000  # Maximum lines of output
    max_concurrent_processes: int = 8  # Maximum concurrent wrapper processes
    
    # Execution settings
    python_executable: str = "python"  # Python executable to use
    working_directory: Optional[str] = None  # Working directory for script execution
    
    # Streaming settings
    stream_buffer_size: int = 1024  # Buffer size for streaming output
    stream_flush_interval: float = 0.1  # Seconds between stream flushes
    
    # Security settings
    allow_network_access: bool = True  # Allow network access in scripts
    allow_file_write: bool = True  # Allow file writing in scripts
    
    @classmethod
    def from_env(cls) -> "WrapperConfig":
        """Create configuration from environment variables."""
        return cls(
            max_execution_time=int(os.getenv("WRAPPER_MAX_EXECUTION_TIME", "300")),
            max_memory_mb=int(os.getenv("WRAPPER_MAX_MEMORY_MB", "512")),
            max_output_lines=int(os.getenv("WRAPPER_MAX_OUTPUT_LINES", "10000")),
            max_concurrent_processes=int(os.getenv("WRAPPER_MAX_CONCURRENT", "8")),
            python_executable=os.getenv("WRAPPER_PYTHON_EXECUTABLE", "python"),
            working_directory=os.getenv("WRAPPER_WORKING_DIR"),
            stream_buffer_size=int(os.getenv("WRAPPER_STREAM_BUFFER", "1024")),
            stream_flush_interval=float(os.getenv("WRAPPER_STREAM_FLUSH", "0.1")),
            allow_network_access=os.getenv("WRAPPER_ALLOW_NETWORK", "true").lower() == "true",
            allow_file_write=os.getenv("WRAPPER_ALLOW_FILE_WRITE", "true").lower() == "true",
        )
    
    def get_subprocess_env(self) -> dict[str, str]:
        """Get environment variables for subprocess execution."""
        env = os.environ.copy()
        
        # Add security restrictions if needed
        if not self.allow_network_access:
            # This is a basic approach - more sophisticated sandboxing would be needed
            # for production use
            env["NO_PROXY"] = "*"
            env["no_proxy"] = "*"
        
        return env
