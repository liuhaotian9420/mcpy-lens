"""
Service manager that coordinates service registry and route management.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from mcpy_lens.routing import RouteManager
from .service_registry import ServiceRegistry
from .health_monitor import HealthMonitor
from .models import ServiceConfig, ServiceStatus, ServiceRegistrationRequest, ToolInfo


class ServiceManager:
    """Manages service lifecycle, registration, and integration with routing."""
    
    def __init__(self, services_dir: Path, wrappers_dir: Path, route_manager: RouteManager):
        self.services_dir = services_dir
        self.wrappers_dir = wrappers_dir
        self.route_manager = route_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize components
        self.service_registry = ServiceRegistry(services_dir)
        self.health_monitor = HealthMonitor(self.service_registry, wrappers_dir)
        
        self._started = False
    
    async def start(self) -> None:
        """Start the service manager."""
        if self._started:
            return
        
        self.logger.info("Starting service manager")
        
        # Start health monitoring
        await self.health_monitor.start()
        
        # Register existing active services with route manager
        await self._register_existing_services()
        
        self._started = True
        self.logger.info("Service manager started successfully")
    
    async def stop(self) -> None:
        """Stop the service manager."""
        if not self._started:
            return
        
        self.logger.info("Stopping service manager")
        
        # Stop health monitoring
        await self.health_monitor.stop()
        
        self._started = False
        self.logger.info("Service manager stopped")
    
    async def _register_existing_services(self) -> None:
        """Register existing active services with the route manager."""
        active_services = self.service_registry.get_active_services()
        
        for service_config in active_services:
            try:
                await self._register_service_routes(service_config)
            except Exception as e:
                self.logger.error(f"Error registering routes for service {service_config.service_id}: {e}")
                # Mark service as error if route registration fails
                await self.service_registry.update_service_status(service_config.service_id, ServiceStatus.ERROR)
    
    async def register_service_from_wrapper(
        self,
        script_id: str,
        wrapper_metadata: Dict[str, Any],
        auto_activate: bool = True
    ) -> ServiceConfig:
        """Register a service automatically from wrapper generation."""
        try:
            # Extract service information from wrapper metadata
            tools = []
            for tool_data in wrapper_metadata.get("tools", []):
                tool = ToolInfo(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("parameters", {}),
                    return_type=tool_data.get("return_type", "Any")
                )
                tools.append(tool)
            
            # Create registration request
            request = ServiceRegistrationRequest(
                name=wrapper_metadata.get("name", f"service_{script_id}"),
                description=wrapper_metadata.get("description", f"Auto-generated service for script {script_id}"),
                service_type=wrapper_metadata.get("type", "function"),
                hosting_mode=wrapper_metadata.get("hosting_mode", "sse"),
                script_id=script_id,
                tools=tools,
                metadata={
                    "auto_generated": True,
                    "wrapper_metadata": wrapper_metadata
                }
            )
            
            # Register service
            service_config = await self.service_registry.register_service(request)
            
            # Auto-activate if requested
            if auto_activate:
                await self.activate_service(service_config.service_id)
            
            self.logger.info(f"Auto-registered service {service_config.service_id} from wrapper")
            return service_config
            
        except Exception as e:
            self.logger.error(f"Error auto-registering service from wrapper: {e}")
            raise
    
    async def register_service(self, request: ServiceRegistrationRequest) -> ServiceConfig:
        """Register a new service manually."""
        service_config = await self.service_registry.register_service(request)
        self.logger.info(f"Manually registered service {service_config.service_id}")
        return service_config
    
    async def activate_service(self, service_id: str) -> bool:
        """Activate a service and register its routes."""
        service_config = self.service_registry.get_service(service_id)
        if not service_config:
            return False
        
        try:
            # Register routes with route manager
            await self._register_service_routes(service_config)
            
            # Update service status
            await self.service_registry.update_service_status(service_id, ServiceStatus.ACTIVE)
            
            self.logger.info(f"Activated service {service_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error activating service {service_id}: {e}")
            await self.service_registry.update_service_status(service_id, ServiceStatus.ERROR)
            return False
    
    async def deactivate_service(self, service_id: str) -> bool:
        """Deactivate a service and unregister its routes."""
        service_config = self.service_registry.get_service(service_id)
        if not service_config:
            return False
        
        try:
            # Unregister routes from route manager
            self.route_manager.unregister_service(service_id)
            
            # Update service status
            await self.service_registry.update_service_status(service_id, ServiceStatus.INACTIVE)
            
            self.logger.info(f"Deactivated service {service_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deactivating service {service_id}: {e}")
            return False
    
    async def unregister_service(self, service_id: str) -> bool:
        """Completely unregister a service."""
        # First deactivate
        await self.deactivate_service(service_id)
        
        # Then unregister from registry
        result = await self.service_registry.unregister_service(service_id)
        
        if result:
            self.logger.info(f"Unregistered service {service_id}")
        
        return result
    
    async def _register_service_routes(self, service_config: ServiceConfig) -> None:
        """Register service routes with the route manager."""
        # For now, we just mark the service as registered in the route manager
        # The actual route handling is done by the adapter layer
        # This is a placeholder for future route registration logic
        
        # Create a dummy router for route manager compatibility
        from fastapi import APIRouter
        router = APIRouter()
        
        # Register with route manager (this marks routes as taken)
        self.route_manager.register_service(
            service_id=service_config.service_id,
            name=service_config.name,
            version="1.0.0",
            router=router,
            metadata={
                "service_type": service_config.service_type.value,
                "hosting_mode": service_config.hosting_mode.value,
                "tools": [tool.to_dict() for tool in service_config.tools],
                "routes": service_config.routes
            }
        )
    
    def get_service(self, service_id: str) -> Optional[ServiceConfig]:
        """Get service configuration."""
        return self.service_registry.get_service(service_id)
    
    def get_service_by_name(self, name: str) -> Optional[ServiceConfig]:
        """Get service configuration by name."""
        return self.service_registry.get_service_by_name(name)
    
    def list_services(self, status_filter: Optional[ServiceStatus] = None) -> List[ServiceConfig]:
        """List services with optional status filter."""
        return self.service_registry.list_services(status_filter)
    
    async def check_service_health(self, service_id: str):
        """Check health of a specific service."""
        return await self.health_monitor.check_service_health(service_id)
    
    def get_service_health(self, service_id: str):
        """Get latest health check result for a service."""
        return self.health_monitor.get_health_result(service_id)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        registry_stats = self.service_registry.get_service_stats()
        health_results = self.health_monitor.get_all_health_results()
        
        return {
            "registry": registry_stats,
            "health_checks": {
                "total_checks": len(health_results),
                "healthy_services": len([r for r in health_results.values() if r.status == ServiceStatus.ACTIVE]),
                "unhealthy_services": len([r for r in health_results.values() if r.status == ServiceStatus.ERROR]),
                "average_response_time": self._calculate_average_response_time(health_results)
            }
        }
    
    def _calculate_average_response_time(self, health_results: Dict[str, Any]) -> float:
        """Calculate average response time from health results."""
        if not health_results:
            return 0.0
        
        total_time = sum(result.response_time_ms for result in health_results.values())
        return total_time / len(health_results)
