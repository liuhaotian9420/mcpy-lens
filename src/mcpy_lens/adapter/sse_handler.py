"""
Server-Sent Events (SSE) handler for MCP adapter.
"""

import asyncio
import json
import logging
import time
from typing import AsyncIterator, Dict, Any, Optional
from dataclasses import dataclass

from .config import AdapterConfig


@dataclass
class SSEEvent:
    """Represents an SSE event."""
    data: str
    event: Optional[str] = None
    id: Optional[str] = None
    retry: Optional[int] = None
    
    def format(self) -> str:
        """Format the event as SSE format."""
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        
        if self.event:
            lines.append(f"event: {self.event}")
        
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        # Split data into multiple lines if needed
        for line in self.data.split('\n'):
            lines.append(f"data: {line}")
        
        # Add empty line to signal end of event
        lines.append("")
        
        return '\n'.join(lines)


class SSEHandler:
    """Handles Server-Sent Events streaming."""
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def stream_responses(
        self,
        response_iterator: AsyncIterator[Dict[str, Any]],
        session_id: str
    ) -> AsyncIterator[str]:
        """Stream responses as SSE events."""
        try:
            # Send initial connection event
            yield self._create_connection_event(session_id)
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(session_id)
            )
            
            try:
                async for response in response_iterator:
                    # Convert response to SSE event
                    event = self._response_to_sse_event(response, session_id)
                    yield event.format()
                    
                    # Check if this is the final response
                    if not response.get("partial", False):
                        break
                
                # Send completion event
                yield self._create_completion_event(session_id)
                
            finally:
                # Cancel heartbeat
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                
        except asyncio.CancelledError:
            self.logger.info(f"SSE stream cancelled for session {session_id}")
            yield self._create_cancellation_event(session_id)
            raise
        except Exception as e:
            self.logger.error(f"Error in SSE stream for session {session_id}: {e}")
            yield self._create_error_event(str(e), session_id)
    
    def _response_to_sse_event(self, response: Dict[str, Any], session_id: str) -> SSEEvent:
        """Convert a JSON-RPC response to an SSE event."""
        # Determine event type
        event_type = None
        if "error" in response:
            event_type = "error"
        elif response.get("partial", False):
            event_type = "partial"
        else:
            event_type = "response"
        
        # Create event
        return SSEEvent(
            data=json.dumps(response),
            event=event_type,
            id=f"{session_id}_{int(time.time() * 1000)}"
        )
    
    def _create_connection_event(self, session_id: str) -> str:
        """Create initial connection event."""
        event = SSEEvent(
            data=json.dumps({
                "type": "connection",
                "session_id": session_id,
                "timestamp": time.time()
            }),
            event="connection",
            id=f"{session_id}_connect"
        )
        return event.format()
    
    def _create_completion_event(self, session_id: str) -> str:
        """Create completion event."""
        event = SSEEvent(
            data=json.dumps({
                "type": "completion",
                "session_id": session_id,
                "timestamp": time.time()
            }),
            event="completion",
            id=f"{session_id}_complete"
        )
        return event.format()
    
    def _create_cancellation_event(self, session_id: str) -> str:
        """Create cancellation event."""
        event = SSEEvent(
            data=json.dumps({
                "type": "cancellation",
                "session_id": session_id,
                "timestamp": time.time()
            }),
            event="cancellation",
            id=f"{session_id}_cancel"
        )
        return event.format()
    
    def _create_error_event(self, error_message: str, session_id: str) -> str:
        """Create error event."""
        event = SSEEvent(
            data=json.dumps({
                "type": "error",
                "message": error_message,
                "session_id": session_id,
                "timestamp": time.time()
            }),
            event="error",
            id=f"{session_id}_error"
        )
        return event.format()
    
    def _create_heartbeat_event(self, session_id: str) -> str:
        """Create heartbeat event."""
        event = SSEEvent(
            data=json.dumps({
                "type": "heartbeat",
                "session_id": session_id,
                "timestamp": time.time()
            }),
            event="heartbeat",
            id=f"{session_id}_heartbeat"
        )
        return event.format()
    
    async def _heartbeat_loop(self, session_id: str) -> AsyncIterator[str]:
        """Generate periodic heartbeat events."""
        while True:
            try:
                await asyncio.sleep(self.config.sse_heartbeat_interval)
                yield self._create_heartbeat_event(session_id)
            except asyncio.CancelledError:
                break
    
    @staticmethod
    def get_sse_headers() -> Dict[str, str]:
        """Get standard SSE headers."""
        return {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
