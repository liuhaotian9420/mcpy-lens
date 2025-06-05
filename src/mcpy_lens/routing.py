"""Dynamic routing management for mcpy-lens."""

import logging
from threading import RLock
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from mcpy_lens.exceptions import DynamicRoutingError


class ServiceInfo:
    """Information about a registered service."""

    def __init__(
        self,
        service_id: str,
        name: str,
        version: str,
        routes: list[str],
        metadata: dict[str, Any],
    ) -> None:
        self.service_id = service_id
        self.name = name
        self.version = version
        self.routes = routes
        self.metadata = metadata
        self.active = True


class RouteManager:
    """Thread-safe manager for dynamic route operations."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._services: dict[str, ServiceInfo] = {}
        self._routes: dict[str, str] = {}  # route_path -> service_id mapping
        self._app: FastAPI | None | None = None

    def attach_app(self, app: FastAPI) -> None:
        """Attach the FastAPI application to this route manager."""
        with self._lock:
            self._app = app

    def register_service(
        self,
        service_id: str,
        name: str,
        version: str,
        router: APIRouter,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a new service with its routes."""
        with self._lock:
            # Check for service ID conflicts
            if service_id in self._services:
                raise DynamicRoutingError(
                    f"Service with ID '{service_id}' already exists",
                    {"existing_service": self._services[service_id].name},
                )            # Extract route paths from router
            route_paths = []
            logical_routes = []  # Routes before service prefixing

            for route in router.routes:
                if isinstance(route, APIRoute):
                    logical_path = route.path  # Original path without service prefix
                    route_path = f"/{service_id}{route.path}"  # Final path with service prefix

                    route_paths.append(route_path)
                    logical_routes.append(logical_path)

                    # Check for logical route conflicts (same base path across services)
                    existing_logical_routes = [
                        path for existing_service_id, service in self._services.items()
                        for path in service.metadata.get('logical_routes', [])
                        if existing_service_id != service_id
                    ]

                    if logical_path in existing_logical_routes:
                        # Find which service has this logical route
                        conflicting_service = None
                        for existing_service_id, service in self._services.items():
                            if logical_path in service.metadata.get('logical_routes', []):
                                conflicting_service = existing_service_id
                                break

                        raise DynamicRoutingError(
                            f"Logical route '{logical_path}' conflicts with existing service",
                            {
                                "conflicting_service": conflicting_service,
                                "requested_service": service_id,
                                "logical_path": logical_path,
                            },
                        )

                    # Check for actual route conflicts (final path conflicts)
                    if route_path in self._routes:
                        conflicting_service = self._routes[route_path]
                        raise DynamicRoutingError(
                            f"Route '{route_path}' conflicts with existing service",
                            {
                                "conflicting_service": conflicting_service,
                                "requested_service": service_id,
                            },
                        )            # Register service
            service_metadata = metadata or {}
            service_metadata['logical_routes'] = logical_routes  # Store logical routes for conflict checking

            service_info = ServiceInfo(
                service_id=service_id,
                name=name,
                version=version,
                routes=route_paths,
                metadata=service_metadata,
            )

            self._services[service_id] = service_info

            # Register routes mapping
            for route_path in route_paths:
                self._routes[route_path] = service_id

            # Add routes to FastAPI app if attached
            if self._app is not None:
                self._add_router_to_app(service_id, router)

            logging.info(
                "Service registered successfully",
                extra={
                    "service_id": service_id,
                    "service_name": name,
                    "routes_count": len(route_paths),
                    "routes": route_paths,
                },
            )

    def unregister_service(self, service_id: str) -> bool:
        """Unregister a service and remove its routes."""
        with self._lock:
            if service_id not in self._services:
                return False

            service_info = self._services[service_id]

            # Remove route mappings
            for route_path in service_info.routes:
                self._routes.pop(route_path, None)

            # Mark service as inactive
            service_info.active = False

            # NOTE: FastAPI doesn't support dynamic route removal easily
            # For now, we mark the service as inactive
            # In production, this would require app restart or more complex routing

            logging.info(
                "Service unregistered",
                extra={
                    "service_id": service_id,
                    "service_name": service_info.name,
                },
            )

            return True

    def get_service(self, service_id: str) -> ServiceInfo | None:
        """Get information about a registered service."""
        with self._lock:
            return self._services.get(service_id)

    def list_services(self) -> list[ServiceInfo]:
        """List all registered services."""
        with self._lock:
            return [service for service in self._services.values() if service.active]

    def get_route_conflicts(self, routes: list[str]) -> list[str]:
        """Check for potential route conflicts."""
        with self._lock:
            conflicts = []
            for route in routes:
                if route in self._routes:
                    conflicts.append(route)
            return conflicts

    def _add_router_to_app(self, service_id: str, router: APIRouter) -> None:
        """Add router to FastAPI app with service prefix."""
        if self._app is None:
            return

        # Add router with service prefix
        self._app.include_router(router, prefix=f"/{service_id}", tags=[service_id])

    async def cleanup(self) -> None:
        """Cleanup resources during application shutdown."""
        with self._lock:
            # Mark all services as inactive
            for service in self._services.values():
                service.active = False

            logging.info(
                "Route manager cleanup completed",
                extra={"services_count": len(self._services)},
            )

    def add_route(
        self,
        path: str,
        endpoint: callable,
        methods: list[str],
        service_id: str,
        name: str = None,
        version: str = "1.0.0",
        metadata: dict[str, Any] = None,
    ) -> None:
        """Add a single route for testing purposes."""
        from fastapi import APIRouter

        # Create a simple router for the single endpoint
        router = APIRouter()

        # Add the route to the router
        router.add_api_route(
            path=path,
            endpoint=endpoint,
            methods=methods,
            name=name or f"{service_id}_route",
        )

        # Register the service with this router
        self.register_service(
            service_id=service_id,
            name=name or service_id,
            version=version,
            router=router,
            metadata=metadata or {},
        )

    def remove_service_routes(self, service_id: str) -> bool:
        """Remove all routes for a service (alias for unregister_service)."""
        return self.unregister_service(service_id)


class ServiceRegistry:
    """Registry for tracking active services and their lifecycle."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._active_services: set[str] = set()
        self._service_processes: dict[str, Any] = {}  # For future process management

    def add_service(self, service_id: str) -> None:
        """Add a service to the active registry."""
        with self._lock:
            self._active_services.add(service_id)

    def remove_service(self, service_id: str) -> bool:
        """Remove a service from the active registry."""
        with self._lock:
            if service_id in self._active_services:
                self._active_services.remove(service_id)
                # Clean up any associated processes
                self._service_processes.pop(service_id, None)
                return True
            return False

    def is_active(self, service_id: str) -> bool:
        """Check if a service is currently active."""
        with self._lock:
            return service_id in self._active_services

    def get_active_services(self) -> set[str]:
        """Get set of currently active service IDs."""
        with self._lock:
            return self._active_services.copy()
