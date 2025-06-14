"""FastAPI application for mcpy-lens."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcpy_lens.config import get_settings
from mcpy_lens.exceptions import setup_exception_handlers
from mcpy_lens.file_routes import file_router
from mcpy_lens.adapter.routes import adapter_router, cleanup_adapter_service
from mcpy_lens.service_registry.routes import service_registry_router, cleanup_service_manager, set_service_manager
from mcpy_lens.service_registry.service_manager import ServiceManager
from mcpy_lens.logging_config import setup_logging
from mcpy_lens.models import HealthCheckResponse
from mcpy_lens.routing import RouteManager

# ——— Application startup and shutdown ———


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management."""
    # Startup: Initialize logging and directories
    settings = get_settings()

    # Set up enhanced logging
    setup_logging()

    # Create and validate required directories
    settings.create_directories()
    if not settings.validate_directories():
        raise RuntimeError("Failed to validate required directories")
    # Initialize route manager
    route_manager = RouteManager()
    app.state.route_manager = route_manager
    route_manager.attach_app(app)

    # Initialize service manager
    app.state.service_manager = ServiceManager(
        services_dir=settings.services_dir,
        wrappers_dir=settings.wrappers_dir,
        route_manager=route_manager
    )
    await app.state.service_manager.start()

    # Set service manager for dependency injection
    set_service_manager(app.state.service_manager)

    # Set service manager in file service for automatic registration
    from mcpy_lens.file_routes import get_file_service
    file_service = get_file_service()
    file_service.set_service_manager(app.state.service_manager)

    logging.info("mcpy-lens application started successfully")

    yield

    # Shutdown: Clean up resources
    if hasattr(app.state, "service_manager"):
        await app.state.service_manager.stop()

    if hasattr(app.state, "route_manager"):
        await app.state.route_manager.cleanup()

    # Clean up adapter service
    await cleanup_adapter_service()

    # Clean up service manager
    await cleanup_service_manager()

    logging.info("mcpy-lens application shutdown complete")


# ——— Application creation ———


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Create FastAPI app with lifespan management
    app = FastAPI(
        title="mcpy-lens",
        description="Web application for uploading Python files and registering them as MCP services",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Setup middleware
    setup_middleware(app)

    # Setup exception handlers
    setup_exception_handlers(app)

    # Add core routes
    setup_routes(app)

    # Ensure route manager is available (especially for testing)
    if not hasattr(app.state, "route_manager"):
        route_manager = RouteManager()
        app.state.route_manager = route_manager
        route_manager.attach_app(app)

    return app


def setup_middleware(app: FastAPI) -> None:
    """Configure middleware for the application."""
    # CORS middleware for web interface
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_routes(app: FastAPI) -> None:
    """Setup core application routes."""

    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check() -> HealthCheckResponse:
        """Health check endpoint."""
        return HealthCheckResponse(
            status="healthy", version="0.1.0", message="mcpy-lens service is running"
        )    # Include file management routes
    app.include_router(file_router)

    # Include adapter routes
    app.include_router(adapter_router)

    # Include service registry routes
    app.include_router(service_registry_router)


# ——— Application instance ———

fastapi_app = create_app()


def main() -> None:
    """Main entry point for running the application."""
    import uvicorn

    from mcpy_lens.config import get_settings

    # Setup logging before running the app
    setup_logging()

    settings = get_settings()

    # Run the FastAPI application with Uvicorn
    uvicorn.run(
        "mcpy_lens.app:fastapi_app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
