"""
Service registry for managing MCP services.
"""

import json
import logging
import uuid
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Any
import aiofiles

from .models import ServiceConfig, ServiceStatus, ServiceRegistrationRequest


class ServiceRegistry:
    """Registry for managing MCP services with file-based persistence."""
    
    def __init__(self, services_dir: Path):
        self.services_dir = services_dir
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._lock = RLock()
        self._services: Dict[str, ServiceConfig] = {}
        self._service_index: Dict[str, str] = {}  # name -> service_id mapping
        
        # Ensure services directory exists
        self.services_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing services
        self._load_services()
    
    def _load_services(self) -> None:
        """Load services from disk on startup."""
        try:
            # Load service files
            service_files = list(self.services_dir.glob("*.json"))
            
            for service_file in service_files:
                try:
                    with open(service_file, 'r', encoding='utf-8') as f:
                        service_data = json.load(f)
                    
                    service_config = ServiceConfig.from_dict(service_data)
                    self._services[service_config.service_id] = service_config
                    self._service_index[service_config.name] = service_config.service_id
                    
                except Exception as e:
                    self.logger.error(f"Error loading service from {service_file}: {e}")
            
            self.logger.info(f"Loaded {len(self._services)} services from disk")
            
        except Exception as e:
            self.logger.error(f"Error loading services: {e}")
    
    async def _save_service(self, service_config: ServiceConfig) -> None:
        """Save service configuration to disk."""
        service_file = self.services_dir / f"{service_config.service_id}.json"
        
        try:
            service_data = service_config.to_dict()
            async with aiofiles.open(service_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(service_data, indent=2))
                
        except Exception as e:
            self.logger.error(f"Error saving service {service_config.service_id}: {e}")
            raise
    
    async def _delete_service_file(self, service_id: str) -> None:
        """Delete service file from disk."""
        service_file = self.services_dir / f"{service_id}.json"
        
        try:
            if service_file.exists():
                service_file.unlink()
                
        except Exception as e:
            self.logger.error(f"Error deleting service file {service_id}: {e}")
            raise
    
    async def register_service(self, request: ServiceRegistrationRequest) -> ServiceConfig:
        """Register a new service."""
        with self._lock:
            # Check for name conflicts
            if request.name in self._service_index:
                existing_id = self._service_index[request.name]
                existing_service = self._services.get(existing_id)
                if existing_service and existing_service.status == ServiceStatus.ACTIVE:
                    raise ValueError(f"Service with name '{request.name}' already exists and is active")
            
            # Generate service ID
            service_id = str(uuid.uuid4())
            
            # Generate routes based on service type
            routes = self._generate_routes(service_id, request)
            
            # Create service configuration
            service_config = request.to_service_config(service_id, routes)
            
            # Store in memory
            self._services[service_id] = service_config
            self._service_index[service_config.name] = service_id
            
            # Save to disk
            await self._save_service(service_config)
            
            self.logger.info(f"Registered service: {service_id} ({request.name})")
            return service_config
    
    def _generate_routes(self, service_id: str, request: ServiceRegistrationRequest) -> List[str]:
        """Generate routes for a service based on its configuration."""
        routes = []
        
        # Base service routes
        routes.extend([
            f"/api/v1/services/{service_id}",
            f"/api/v1/services/{service_id}/health",
            f"/api/v1/services/{service_id}/tools"
        ])
        
        # Add adapter routes if using SSE hosting
        if request.hosting_mode.value == "sse":
            routes.extend([
                f"/api/v1/mcp/{service_id}",
                f"/api/v1/stream/{service_id}"
            ])
        
        return routes
    
    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service."""
        with self._lock:
            if service_id not in self._services:
                return False
            
            service_config = self._services[service_id]
            
            # Remove from memory
            del self._services[service_id]
            if service_config.name in self._service_index:
                del self._service_index[service_config.name]
            
            # Delete from disk
            await self._delete_service_file(service_id)
            
            self.logger.info(f"Unregistered service: {service_id} ({service_config.name})")
            return True
    
    async def update_service_status(self, service_id: str, status: ServiceStatus) -> bool:
        """Update service status."""
        with self._lock:
            if service_id not in self._services:
                return False
            
            service_config = self._services[service_id]
            service_config.update_status(status)
            
            # Save to disk
            await self._save_service(service_config)
            
            self.logger.debug(f"Updated service {service_id} status to {status.value}")
            return True
    
    def get_service(self, service_id: str) -> Optional[ServiceConfig]:
        """Get service configuration by ID."""
        with self._lock:
            return self._services.get(service_id)
    
    def get_service_by_name(self, name: str) -> Optional[ServiceConfig]:
        """Get service configuration by name."""
        with self._lock:
            service_id = self._service_index.get(name)
            if service_id:
                return self._services.get(service_id)
            return None
    
    def list_services(self, status_filter: Optional[ServiceStatus] = None) -> List[ServiceConfig]:
        """List all services, optionally filtered by status."""
        with self._lock:
            services = list(self._services.values())
            
            if status_filter:
                services = [s for s in services if s.status == status_filter]
            
            return services
    
    def get_active_services(self) -> List[ServiceConfig]:
        """Get all active services."""
        return self.list_services(ServiceStatus.ACTIVE)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service registry statistics."""
        with self._lock:
            total_services = len(self._services)
            active_services = len([s for s in self._services.values() if s.status == ServiceStatus.ACTIVE])
            inactive_services = len([s for s in self._services.values() if s.status == ServiceStatus.INACTIVE])
            error_services = len([s for s in self._services.values() if s.status == ServiceStatus.ERROR])
            
            return {
                "total_services": total_services,
                "active_services": active_services,
                "inactive_services": inactive_services,
                "error_services": error_services,
                "services_by_type": self._get_services_by_type(),
                "services_by_hosting_mode": self._get_services_by_hosting_mode()
            }
    
    def _get_services_by_type(self) -> Dict[str, int]:
        """Get service count by type."""
        type_counts = {}
        for service in self._services.values():
            service_type = service.service_type.value
            type_counts[service_type] = type_counts.get(service_type, 0) + 1
        return type_counts
    
    def _get_services_by_hosting_mode(self) -> Dict[str, int]:
        """Get service count by hosting mode."""
        mode_counts = {}
        for service in self._services.values():
            hosting_mode = service.hosting_mode.value
            mode_counts[hosting_mode] = mode_counts.get(hosting_mode, 0) + 1
        return mode_counts
