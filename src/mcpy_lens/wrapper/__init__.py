"""
MCP-compatible wrapper framework for Python scripts and functions.

This module provides the core wrapper functionality to convert Python scripts
into MCP-compatible tools using JSON-RPC protocol over STDIO.
"""

from .base import WrapperBase
from .script_wrapper import ScriptWrapper
from .json_rpc import JSONRPCHandler
from .config import WrapperConfig

__all__ = [
    "WrapperBase",
    "ScriptWrapper", 
    "JSONRPCHandler",
    "WrapperConfig"
]
