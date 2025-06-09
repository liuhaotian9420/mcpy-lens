"""
Main adapter service that coordinates all components.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator

from .config import AdapterConfig
from .session_manager import SessionManager
from .process_manager import ProcessManager
from .cache_manager import CacheManager
from .sse_handler import SSEHandler


class AdapterService:
    """Main service that coordinates HTTP-to-STDIO bridging."""
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        self.config = config or AdapterConfig.from_env()
        self.config.validate()
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize components
        self.session_manager = SessionManager(self.config)
        self.process_manager = ProcessManager(self.config)
        self.cache_manager = CacheManager(self.config)
        self.sse_handler = SSEHandler(self.config)
        
        self._started = False
    
    async def start(self) -> None:
        """Start the adapter service."""
        if self._started:
            return
        
        self.logger.info("Starting MCP adapter service")
        
        # Start all components
        await self.session_manager.start()
        await self.process_manager.start()
        await self.cache_manager.start()
        
        self._started = True
        self.logger.info("MCP adapter service started successfully")
    
    async def stop(self) -> None:
        """Stop the adapter service."""
        if not self._started:
            return
        
        self.logger.info("Stopping MCP adapter service")
        
        # Stop all components
        await self.cache_manager.stop()
        await self.process_manager.stop()
        await self.session_manager.stop()
        
        self._started = False
        self.logger.info("MCP adapter service stopped")
    
    def create_session(self, client_info: Optional[Dict[str, str]] = None) -> str:
        """Create a new session for request correlation."""
        return self.session_manager.create_session(client_info)
    
    async def execute_request(
        self,
        service_id: str,
        request_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute a JSON-RPC request and yield streaming responses."""
        # Generate request ID if not provided
        request_id = request_data.get("id") or str(uuid.uuid4())
        request_data["id"] = request_id
        
        # Validate session
        if session_id:
            session = self.session_manager.get_session(session_id)
            if not session:
                yield {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid session ID"
                    }
                }
                return
            
            # Add request to session
            self.session_manager.add_request_to_session(session_id, request_id)
        
        try:
            # Check cache first
            cache_key = None
            if self.cache_manager.is_cacheable_request(request_data):
                cache_key = self.cache_manager.generate_cache_key(
                    request_data.get("method", ""),
                    request_data.get("params", {})
                )
                cached_response = self.cache_manager.get(cache_key)
                if cached_response:
                    self.logger.debug(f"Returning cached response for request {request_id}")
                    yield cached_response
                    return
            
            # Find wrapper path for service
            wrapper_path = await self._get_wrapper_path(service_id)
            if not wrapper_path:
                yield {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Service '{service_id}' not found"
                    }
                }
                return
            
            # Execute request through process manager
            responses = []
            async for response in self.process_manager.execute_request(
                wrapper_path, request_data, request_id
            ):
                responses.append(response)
                yield response
            
            # Cache the final response if cacheable
            if cache_key and responses:
                final_response = responses[-1]
                if "error" not in final_response:
                    self.cache_manager.put(cache_key, final_response)
        
        except Exception as e:
            self.logger.error(f"Error executing request {request_id}: {e}")
            yield {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
        
        finally:
            # Remove request from session
            if session_id:
                self.session_manager.remove_request_from_session(session_id, request_id)
    
    async def stream_sse_responses(
        self,
        service_id: str,
        request_data: Dict[str, Any],
        session_id: str
    ) -> AsyncIterator[str]:
        """Execute request and stream responses as SSE events."""
        response_iterator = self.execute_request(service_id, request_data, session_id)
        async for sse_event in self.sse_handler.stream_responses(response_iterator, session_id):
            yield sse_event
    
    async def _get_wrapper_path(self, service_id: str) -> Optional[Path]:
        """Get the wrapper path for a service ID."""
        # This would typically look up the service in a registry
        # For now, we'll assume the service_id corresponds to a wrapper directory
        from mcpy_lens.config import get_settings
        
        settings = get_settings()
        wrapper_dir = settings.wrappers_dir / service_id
        
        if wrapper_dir.exists():
            # Look for the main wrapper script
            wrapper_script = wrapper_dir / f"{service_id}_wrapper.py"
            if wrapper_script.exists():
                return wrapper_script
        
        return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the adapter service."""
        return {
            "status": "healthy" if self._started else "stopped",
            "components": {
                "session_manager": self.session_manager.get_session_stats(),
                "process_manager": self.process_manager.get_process_stats(),
                "cache_manager": self.cache_manager.get_cache_stats()
            },
            "config": {
                "max_concurrent_requests": self.config.max_concurrent_requests,
                "max_sessions": self.config.max_sessions,
                "cache_enabled": self.config.cache_enabled
            }
        }
    
    def validate_request(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a JSON-RPC request."""
        # Check required fields
        if not isinstance(request_data, dict):
            return {
                "code": -32600,
                "message": "Invalid Request - request must be a JSON object"
            }
        
        if "jsonrpc" not in request_data:
            return {
                "code": -32600,
                "message": "Invalid Request - missing 'jsonrpc' field"
            }
        
        if request_data.get("jsonrpc") != "2.0":
            return {
                "code": -32600,
                "message": "Invalid Request - 'jsonrpc' must be '2.0'"
            }
        
        if "method" not in request_data:
            return {
                "code": -32600,
                "message": "Invalid Request - missing 'method' field"
            }
        
        # Method should be a string
        if not isinstance(request_data.get("method"), str):
            return {
                "code": -32600,
                "message": "Invalid Request - 'method' must be a string"
            }
        
        return None  # Valid request
