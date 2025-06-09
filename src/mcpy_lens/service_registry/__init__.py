"""
Dynamic service registration system for mcpy-lens.

This module provides the service registry functionality for real-time
addition and removal of MCP services without server restart.
"""

from .service_registry import ServiceRegistry
from .service_manager import ServiceManager
from .health_monitor import HealthMonitor
from .models import ServiceConfig, ServiceStatus, HealthCheckResult

__all__ = [
    "ServiceRegistry",
    "ServiceManager", 
    "HealthMonitor",
    "ServiceConfig",
    "ServiceStatus",
    "HealthCheckResult"
]
