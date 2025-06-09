"""
FastAPI routes for service registry management.
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from .service_manager import ServiceManager
from .models import ServiceConfig, ServiceStatus, ServiceRegistrationRequest, ToolInfo


# Request/Response models
class ToolInfoModel(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    return_type: str


class ServiceRegistrationModel(BaseModel):
    name: str
    description: str
    service_type: str
    hosting_mode: str
    script_id: str
    tools: List[ToolInfoModel]
    config: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class ServiceConfigResponse(BaseModel):
    service_id: str
    name: str
    description: str
    service_type: str
    hosting_mode: str
    script_id: str
    tools: List[ToolInfoModel]
    routes: List[str]
    status: str
    created_at: str
    updated_at: str
    config: Dict[str, Any]
    metadata: Dict[str, Any]


class ServiceListResponse(BaseModel):
    services: List[ServiceConfigResponse]
    total: int


class ServiceStatsResponse(BaseModel):
    registry: Dict[str, Any]
    health_checks: Dict[str, Any]


class HealthCheckResponse(BaseModel):
    service_id: str
    status: str
    timestamp: str
    response_time_ms: float
    details: Dict[str, Any]
    error_message: Optional[str] = None


# Global service manager instance
_service_manager: Optional[ServiceManager] = None


async def get_service_manager() -> ServiceManager:
    """Dependency to get the service manager instance."""
    global _service_manager
    if _service_manager is None:
        raise HTTPException(status_code=500, detail="Service manager not initialized")
    return _service_manager


def set_service_manager(service_manager: ServiceManager) -> None:
    """Set the global service manager instance."""
    global _service_manager
    _service_manager = service_manager


# Create router
service_registry_router = APIRouter(prefix="/api/v1/services", tags=["service-registry"])


@service_registry_router.post("/register", response_model=ServiceConfigResponse)
async def register_service(
    request: ServiceRegistrationModel,
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Register a new service."""
    try:
        # Convert to internal model
        tools = [
            ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
                return_type=tool.return_type
            )
            for tool in request.tools
        ]
        
        registration_request = ServiceRegistrationRequest(
            name=request.name,
            description=request.description,
            service_type=request.service_type,
            hosting_mode=request.hosting_mode,
            script_id=request.script_id,
            tools=tools,
            config=request.config,
            metadata=request.metadata
        )
        
        service_config = await service_manager.register_service(registration_request)
        
        # Convert to response model
        return ServiceConfigResponse(**service_config.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error registering service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register service: {str(e)}")


@service_registry_router.get("/", response_model=ServiceListResponse)
async def list_services(
    status: Optional[str] = Query(None, description="Filter by service status"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """List all services with optional status filter."""
    try:
        status_filter = None
        if status:
            try:
                status_filter = ServiceStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        services = service_manager.list_services(status_filter)
        
        service_responses = [
            ServiceConfigResponse(**service.to_dict())
            for service in services
        ]
        
        return ServiceListResponse(
            services=service_responses,
            total=len(service_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list services: {str(e)}")


@service_registry_router.get("/{service_id}", response_model=ServiceConfigResponse)
async def get_service(
    service_id: str,
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Get service configuration by ID."""
    try:
        service_config = service_manager.get_service(service_id)
        if not service_config:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        
        return ServiceConfigResponse(**service_config.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service: {str(e)}")


@service_registry_router.post("/{service_id}/activate")
async def activate_service(
    service_id: str,
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Activate a service."""
    try:
        success = await service_manager.activate_service(service_id)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to activate service {service_id}")
        
        return {"message": f"Service {service_id} activated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error activating service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to activate service: {str(e)}")


@service_registry_router.post("/{service_id}/deactivate")
async def deactivate_service(
    service_id: str,
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Deactivate a service."""
    try:
        success = await service_manager.deactivate_service(service_id)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to deactivate service {service_id}")
        
        return {"message": f"Service {service_id} deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deactivating service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to deactivate service: {str(e)}")


@service_registry_router.delete("/{service_id}")
async def unregister_service(
    service_id: str,
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Unregister a service completely."""
    try:
        success = await service_manager.unregister_service(service_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        
        return {"message": f"Service {service_id} unregistered successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error unregistering service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unregister service: {str(e)}")


@service_registry_router.get("/{service_id}/health", response_model=HealthCheckResponse)
async def check_service_health(
    service_id: str,
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Check health of a specific service."""
    try:
        health_result = await service_manager.check_service_health(service_id)
        
        return HealthCheckResponse(**health_result.to_dict())
        
    except Exception as e:
        logging.error(f"Error checking health for service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check service health: {str(e)}")


@service_registry_router.get("/{service_id}/tools")
async def get_service_tools(
    service_id: str,
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Get tools exposed by a service."""
    try:
        service_config = service_manager.get_service(service_id)
        if not service_config:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        
        tools = [tool.to_dict() for tool in service_config.tools]
        
        return {
            "service_id": service_id,
            "tools": tools,
            "total": len(tools)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting tools for service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service tools: {str(e)}")


@service_registry_router.get("/stats/overview", response_model=ServiceStatsResponse)
async def get_service_stats(
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """Get comprehensive service statistics."""
    try:
        stats = service_manager.get_service_stats()
        return ServiceStatsResponse(**stats)
        
    except Exception as e:
        logging.error(f"Error getting service stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service stats: {str(e)}")


# Cleanup function for application shutdown
async def cleanup_service_manager():
    """Cleanup the service manager on application shutdown."""
    global _service_manager
    if _service_manager:
        await _service_manager.stop()
        _service_manager = None
