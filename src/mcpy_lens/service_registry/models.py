"""
Data models for the service registry.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime


class ServiceStatus(str, Enum):
    """Service status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class ServiceType(str, Enum):
    """Service type enumeration."""
    FUNCTION = "function"
    EXECUTABLE = "executable"


class HostingMode(str, Enum):
    """Service hosting mode enumeration."""
    STDIO = "stdio"
    SSE = "sse"


@dataclass
class ToolInfo:
    """Information about a tool exposed by a service."""
    name: str
    description: str
    parameters: Dict[str, Any]
    return_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "return_type": self.return_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolInfo":
        return cls(
            name=data["name"],
            description=data["description"],
            parameters=data["parameters"],
            return_type=data["return_type"]
        )


@dataclass
class ServiceConfig:
    """Service configuration model."""
    service_id: str
    name: str
    description: str
    service_type: ServiceType
    hosting_mode: HostingMode
    script_id: str
    tools: List[ToolInfo]
    routes: List[str]
    status: ServiceStatus = ServiceStatus.INACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_id": self.service_id,
            "name": self.name,
            "description": self.description,
            "type": self.service_type.value,
            "hosting_mode": self.hosting_mode.value,
            "script_id": self.script_id,
            "tools": [tool.to_dict() for tool in self.tools],
            "routes": self.routes,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "config": self.config,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceConfig":
        """Create from dictionary."""
        return cls(
            service_id=data["service_id"],
            name=data["name"],
            description=data["description"],
            service_type=ServiceType(data["type"]),
            hosting_mode=HostingMode(data["hosting_mode"]),
            script_id=data["script_id"],
            tools=[ToolInfo.from_dict(tool) for tool in data["tools"]],
            routes=data["routes"],
            status=ServiceStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            config=data.get("config", {}),
            metadata=data.get("metadata", {})
        )
    
    def update_status(self, status: ServiceStatus) -> None:
        """Update service status and timestamp."""
        self.status = status
        self.updated_at = datetime.now()


@dataclass
class HealthCheckResult:
    """Result of a service health check."""
    service_id: str
    status: ServiceStatus
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_id": self.service_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealthCheckResult":
        """Create from dictionary."""
        return cls(
            service_id=data["service_id"],
            status=ServiceStatus(data["status"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            response_time_ms=data["response_time_ms"],
            details=data.get("details", {}),
            error_message=data.get("error_message")
        )


@dataclass
class ServiceRegistrationRequest:
    """Request model for service registration."""
    name: str
    description: str
    service_type: ServiceType
    hosting_mode: HostingMode
    script_id: str
    tools: List[ToolInfo]
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_service_config(self, service_id: str, routes: List[str]) -> ServiceConfig:
        """Convert to ServiceConfig."""
        return ServiceConfig(
            service_id=service_id,
            name=self.name,
            description=self.description,
            service_type=self.service_type,
            hosting_mode=self.hosting_mode,
            script_id=self.script_id,
            tools=self.tools,
            routes=routes,
            config=self.config,
            metadata=self.metadata
        )
