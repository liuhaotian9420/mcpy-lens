"""
Base wrapper class providing core MCP functionality.
"""

import sys
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncIterator
from pathlib import Path

from .json_rpc import JSONRPCHandler, JSONRPCRequest, JSONRPCResponse, JSONRPCError
from .config import WrapperConfig

logger = logging.getLogger(__name__)


class WrapperBase(ABC):
    """Base class for MCP-compatible wrappers."""
    
    def __init__(self, config: Optional[WrapperConfig] = None):
        self.config = config or WrapperConfig.from_env()
        self.json_rpc = JSONRPCHandler()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Setup logging with sanitized wrapper errors
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging with appropriate levels."""
        # Configure wrapper-specific logging (sanitized)
        wrapper_logger = logging.getLogger("mcpy_lens.wrapper")
        wrapper_logger.setLevel(logging.INFO)
        
        # Configure script execution logging (full transparency)
        script_logger = logging.getLogger("mcpy_lens.wrapper.script_execution")
        script_logger.setLevel(logging.DEBUG)
    
    async def run(self):
        """Main entry point for wrapper execution."""
        self.logger.info("Starting MCP wrapper")
        
        try:
            async for line in self._read_stdin():
                if line.strip():
                    await self._process_line(line)
        except KeyboardInterrupt:
            self.logger.info("Wrapper interrupted by user")
        except Exception as e:
            self.logger.error(f"Wrapper error: {str(e)}")  # Sanitized logging
        finally:
            self.logger.info("Wrapper shutting down")
    
    async def _read_stdin(self) -> AsyncIterator[str]:
        """Read lines from stdin asynchronously."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                yield line.decode('utf-8')
            except Exception as e:
                self.logger.error(f"Error reading stdin: {str(e)}")
                break
    
    async def _process_line(self, line: str):
        """Process a single line of JSON-RPC input."""
        request = self.json_rpc.parse_request(line)
        
        if not request:
            response = self.json_rpc.create_error_response(
                None, JSONRPCError.PARSE_ERROR
            )
            await self._send_response(response)
            return
        
        # Validate request
        error = self.json_rpc.validate_request(request)
        if error:
            response = self.json_rpc.create_error_response(request.id, error)
            await self._send_response(response)
            return
        
        # Process request
        try:
            await self._handle_request(request)
        except Exception as e:
            self.logger.error(f"Request handling error: {str(e)}")  # Sanitized
            response = self.json_rpc.create_error_response(
                request.id, 
                JSONRPCError.INTERNAL_ERROR,
                {"message": "Internal wrapper error"}  # Sanitized message
            )
            await self._send_response(response)
    
    async def _handle_request(self, request: JSONRPCRequest):
        """Handle a validated JSON-RPC request."""
        method = request.method.lower()
        
        if method == "listtools":
            await self._handle_list_tools(request)
        elif method == "calltool":
            await self._handle_call_tool(request)
        elif method == "gettoolinfo":
            await self._handle_get_tool_info(request)
        elif method == "healthcheck":
            await self._handle_health_check(request)
        else:
            response = self.json_rpc.create_error_response(
                request.id, JSONRPCError.METHOD_NOT_FOUND
            )
            await self._send_response(response)
    
    async def _send_response(self, response: JSONRPCResponse):
        """Send a JSON-RPC response to stdout."""
        try:
            json_str = response.to_json()
            print(json_str, flush=True)
        except Exception as e:
            self.logger.error(f"Error sending response: {str(e)}")
    
    async def _handle_health_check(self, request: JSONRPCRequest):
        """Handle health check requests."""
        response = self.json_rpc.create_response(
            request.id,
            {"status": "healthy", "wrapper": self.__class__.__name__}
        )
        await self._send_response(response)
    
    @abstractmethod
    async def _handle_list_tools(self, request: JSONRPCRequest):
        """Handle list tools requests. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def _handle_call_tool(self, request: JSONRPCRequest):
        """Handle call tool requests. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def _handle_get_tool_info(self, request: JSONRPCRequest):
        """Handle get tool info requests. Must be implemented by subclasses."""
        pass


def main():
    """Main entry point for standalone wrapper execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Wrapper")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--metadata", help="Path to tool metadata file", required=True)
    parser.add_argument("--script", help="Path to Python script", required=True)
    
    args = parser.parse_args()
    
    # Import here to avoid circular imports
    from .script_wrapper import ScriptWrapper
    
    # Load configuration
    config = WrapperConfig.from_env()
    
    # Create and run wrapper
    wrapper = ScriptWrapper(
        script_path=Path(args.script),
        metadata_path=Path(args.metadata),
        config=config
    )
    
    asyncio.run(wrapper.run())


if __name__ == "__main__":
    main()
