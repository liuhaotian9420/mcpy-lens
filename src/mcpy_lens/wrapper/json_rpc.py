"""
JSON-RPC 2.0 protocol handler for MCP communication.
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JSONRPCRequest:
    """Represents a JSON-RPC 2.0 request."""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    jsonrpc: str = "2.0"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONRPCRequest":
        """Create request from dictionary."""
        return cls(
            method=data["method"],
            params=data.get("params"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0")
        )


@dataclass
class JSONRPCResponse:
    """Represents a JSON-RPC 2.0 response."""
    id: Optional[Union[str, int]]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    jsonrpc: str = "2.0"
    partial: bool = False  # For streaming responses
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        response = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        
        if self.partial:
            response["partial"] = True
            response["data"] = self.result
        elif self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result
            
        return response
    
    def to_json(self) -> str:
        """Convert response to JSON string."""
        return json.dumps(self.to_dict())


class JSONRPCError:
    """Standard JSON-RPC error codes and messages."""
    
    # Standard errors
    PARSE_ERROR = {"code": -32700, "message": "Parse error"}
    INVALID_REQUEST = {"code": -32600, "message": "Invalid Request"}
    METHOD_NOT_FOUND = {"code": -32601, "message": "Method not found"}
    INVALID_PARAMS = {"code": -32602, "message": "Invalid params"}
    INTERNAL_ERROR = {"code": -32603, "message": "Internal error"}
    
    # Custom application errors (-32000 to -32099)
    EXECUTION_ERROR = {"code": -32000, "message": "Script execution error"}
    TIMEOUT_ERROR = {"code": -32001, "message": "Execution timeout"}
    RESOURCE_ERROR = {"code": -32002, "message": "Resource limit exceeded"}
    VALIDATION_ERROR = {"code": -32003, "message": "Parameter validation error"}
    
    @staticmethod
    def create_error(error_type: Dict[str, Any], data: Optional[Any] = None) -> Dict[str, Any]:
        """Create an error response with optional additional data."""
        error = error_type.copy()
        if data:
            error["data"] = data
        return error


class JSONRPCHandler:
    """Handles JSON-RPC 2.0 protocol communication."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def parse_request(self, json_line: str) -> Optional[JSONRPCRequest]:
        """Parse a JSON-RPC request from a JSON string."""
        try:
            data = json.loads(json_line.strip())
            
            # Validate required fields
            if not isinstance(data, dict):
                return None
            
            if "method" not in data:
                return None
            
            return JSONRPCRequest.from_dict(data)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Request parsing error: {e}")
            return None
    
    def create_response(
        self, 
        request_id: Optional[Union[str, int]], 
        result: Optional[Any] = None,
        error: Optional[Dict[str, Any]] = None,
        partial: bool = False
    ) -> JSONRPCResponse:
        """Create a JSON-RPC response."""
        return JSONRPCResponse(
            id=request_id,
            result=result,
            error=error,
            partial=partial
        )
    
    def create_error_response(
        self, 
        request_id: Optional[Union[str, int]], 
        error_type: Dict[str, Any],
        data: Optional[Any] = None
    ) -> JSONRPCResponse:
        """Create an error response."""
        error = JSONRPCError.create_error(error_type, data)
        return JSONRPCResponse(id=request_id, error=error)
    
    def validate_request(self, request: JSONRPCRequest) -> Optional[Dict[str, Any]]:
        """Validate a JSON-RPC request. Returns error dict if invalid, None if valid."""
        if request.jsonrpc != "2.0":
            return JSONRPCError.INVALID_REQUEST
        
        if not request.method:
            return JSONRPCError.INVALID_REQUEST
        
        # Method-specific validation can be added here
        return None
