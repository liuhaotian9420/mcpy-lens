"""
FastAPI routes for the MCP adapter.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .adapter_service import AdapterService
from .config import AdapterConfig
from .sse_handler import SSEHandler


# Request/Response models
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class SessionCreateRequest(BaseModel):
    client_info: Optional[Dict[str, str]] = None


class SessionCreateResponse(BaseModel):
    session_id: str


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, Any]
    config: Dict[str, Any]


# Global adapter service instance
_adapter_service: Optional[AdapterService] = None


async def get_adapter_service() -> AdapterService:
    """Dependency to get the adapter service instance."""
    global _adapter_service
    if _adapter_service is None:
        config = AdapterConfig.from_env()
        _adapter_service = AdapterService(config)
        await _adapter_service.start()
    return _adapter_service


# Create router
adapter_router = APIRouter(prefix="/api/v1", tags=["adapter"])


@adapter_router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    request: SessionCreateRequest,
    adapter_service: AdapterService = Depends(get_adapter_service)
):
    """Create a new session for request correlation."""
    try:
        session_id = adapter_service.create_session(request.client_info)
        return SessionCreateResponse(session_id=session_id)
    except Exception as e:
        logging.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@adapter_router.post("/mcp/{service_id}")
async def execute_mcp_request(
    service_id: str,
    request: JSONRPCRequest,
    session_id: Optional[str] = Query(None, description="Session ID for request correlation"),
    adapter_service: AdapterService = Depends(get_adapter_service)
):
    """Execute a JSON-RPC request against a specific MCP service."""
    try:
        # Validate request
        request_data = request.dict()
        validation_error = adapter_service.validate_request(request_data)
        if validation_error:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON-RPC request: {validation_error['message']}"
            )
        
        # Execute request and collect all responses
        responses = []
        async for response in adapter_service.execute_request(
            service_id, request_data, session_id
        ):
            responses.append(response)
        
        # Return the final response
        if responses:
            return responses[-1]
        else:
            raise HTTPException(
                status_code=500,
                detail="No response received from service"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error executing MCP request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@adapter_router.get("/stream/{service_id}")
async def stream_mcp_responses(
    service_id: str,
    session_id: str = Query(..., description="Session ID for request correlation"),
    adapter_service: AdapterService = Depends(get_adapter_service)
):
    """Stream MCP responses as Server-Sent Events."""
    try:
        # Validate session
        session = adapter_service.session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        # This endpoint expects the actual JSON-RPC request to be sent
        # via the POST endpoint, and this stream will deliver the responses
        # For now, we'll create a simple stream that waits for requests
        
        async def event_stream():
            try:
                # Send initial connection event
                sse_handler = SSEHandler(adapter_service.config)
                yield sse_handler._create_connection_event(session_id)
                
                # Keep connection alive with heartbeats
                # In a real implementation, this would listen for actual requests
                # and stream their responses
                import asyncio
                while True:
                    await asyncio.sleep(adapter_service.config.sse_heartbeat_interval)
                    yield sse_handler._create_heartbeat_event(session_id)
                    
            except Exception as e:
                logging.error(f"Error in SSE stream: {e}")
                yield sse_handler._create_error_event(str(e), session_id)
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers=SSEHandler.get_sse_headers()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error setting up SSE stream: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup stream: {str(e)}"
        )


@adapter_router.post("/stream/{service_id}")
async def execute_streaming_request(
    service_id: str,
    request: JSONRPCRequest,
    session_id: str = Query(..., description="Session ID for request correlation"),
    adapter_service: AdapterService = Depends(get_adapter_service)
):
    """Execute a JSON-RPC request and stream responses as SSE."""
    try:
        # Validate request
        request_data = request.dict()
        validation_error = adapter_service.validate_request(request_data)
        if validation_error:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON-RPC request: {validation_error['message']}"
            )
        
        # Validate session
        session = adapter_service.session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        # Stream responses as SSE
        async def event_stream():
            async for sse_event in adapter_service.stream_sse_responses(
                service_id, request_data, session_id
            ):
                yield sse_event
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers=SSEHandler.get_sse_headers()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error executing streaming request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@adapter_router.get("/services/{service_id}/health", response_model=HealthResponse)
async def get_service_health(
    service_id: str,
    adapter_service: AdapterService = Depends(get_adapter_service)
):
    """Get health status of a specific service."""
    try:
        # Get overall adapter health
        health_status = adapter_service.get_health_status()
        
        # Add service-specific information
        health_status["service_id"] = service_id
        
        return HealthResponse(**health_status)
    
    except Exception as e:
        logging.error(f"Error getting service health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get health status: {str(e)}"
        )


@adapter_router.get("/health", response_model=HealthResponse)
async def get_adapter_health(
    adapter_service: AdapterService = Depends(get_adapter_service)
):
    """Get health status of the adapter service."""
    try:
        health_status = adapter_service.get_health_status()
        return HealthResponse(**health_status)
    
    except Exception as e:
        logging.error(f"Error getting adapter health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get health status: {str(e)}"
        )


@adapter_router.get("/stats")
async def get_adapter_stats(
    adapter_service: AdapterService = Depends(get_adapter_service)
):
    """Get detailed statistics about the adapter service."""
    try:
        return {
            "sessions": adapter_service.session_manager.get_session_stats(),
            "processes": adapter_service.process_manager.get_process_stats(),
            "cache": adapter_service.cache_manager.get_cache_stats()
        }
    
    except Exception as e:
        logging.error(f"Error getting adapter stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


# Cleanup function for application shutdown
async def cleanup_adapter_service():
    """Cleanup the adapter service on application shutdown."""
    global _adapter_service
    if _adapter_service:
        await _adapter_service.stop()
        _adapter_service = None
