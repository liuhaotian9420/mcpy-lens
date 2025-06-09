"""
MCP Adapter layer for bridging HTTP requests to STDIO interfaces.

This module provides the adapter functionality to convert HTTP requests
into subprocess communication with MCP wrappers and stream responses
back to clients using Server-Sent Events (SSE).
"""

from .config import AdapterConfig
from .session_manager import SessionManager
from .process_manager import ProcessManager
from .cache_manager import CacheManager
from .sse_handler import SSEHandler
from .adapter_service import AdapterService

__all__ = [
    "AdapterConfig",
    "SessionManager", 
    "ProcessManager",
    "CacheManager",
    "SSEHandler",
    "AdapterService"
]
