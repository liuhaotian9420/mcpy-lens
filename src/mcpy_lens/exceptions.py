"""Exception handling for mcpy-lens."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from mcpy_lens.models import ErrorResponse

# ——— Custom exceptions ———


class McpyLensException(Exception):
    """Base exception for mcpy-lens application."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class FileUploadError(McpyLensException):
    """Exception raised during file upload operations."""

    pass


class ToolDiscoveryError(McpyLensException):
    """Exception raised during tool discovery operations."""

    pass


class ServiceRegistrationError(McpyLensException):
    """Exception raised during service registration operations."""

    pass


class DynamicRoutingError(McpyLensException):
    """Exception raised during dynamic routing operations."""

    pass


# ——— Exception handlers ———


async def mcpy_lens_exception_handler(
    request: Request, exc: McpyLensException
) -> JSONResponse:
    """Handle custom mcpy-lens exceptions."""
    logging.error(
        "McpyLens exception occurred",
        extra={
            "error_type": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.message,
            details=exc.details,
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logging.warning(
        "HTTP exception occurred",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPException",
            message=str(exc.detail),
        ).model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logging.exception(
        "Unhandled exception occurred",
        extra={
            "error_type": exc.__class__.__name__,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An internal server error occurred",
        ).model_dump(),
    )


# ——— Setup function ———


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for the FastAPI application."""
    app.add_exception_handler(McpyLensException, mcpy_lens_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
