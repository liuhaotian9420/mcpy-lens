"""
Unit tests for JSON-RPC protocol handling.
"""

import json
import pytest
from mcpy_lens.wrapper.json_rpc import (
    JSONRPCHandler, 
    JSONRPCRequest, 
    JSONRPCResponse, 
    JSONRPCError
)


class TestJSONRPCRequest:
    """Test JSONRPCRequest class."""
    
    def test_from_dict_basic(self):
        """Test creating request from dictionary."""
        data = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "id": "123"
        }
        request = JSONRPCRequest.from_dict(data)
        
        assert request.method == "test_method"
        assert request.id == "123"
        assert request.jsonrpc == "2.0"
        assert request.params is None
    
    def test_from_dict_with_params(self):
        """Test creating request with parameters."""
        data = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "params": {"arg1": "value1"},
            "id": "123"
        }
        request = JSONRPCRequest.from_dict(data)
        
        assert request.params == {"arg1": "value1"}


class TestJSONRPCResponse:
    """Test JSONRPCResponse class."""
    
    def test_to_dict_success(self):
        """Test converting successful response to dictionary."""
        response = JSONRPCResponse(id="123", result={"data": "test"})
        result = response.to_dict()
        
        expected = {
            "jsonrpc": "2.0",
            "id": "123",
            "result": {"data": "test"}
        }
        assert result == expected
    
    def test_to_dict_error(self):
        """Test converting error response to dictionary."""
        error = {"code": -32000, "message": "Test error"}
        response = JSONRPCResponse(id="123", error=error)
        result = response.to_dict()
        
        expected = {
            "jsonrpc": "2.0",
            "id": "123",
            "error": error
        }
        assert result == expected
    
    def test_to_dict_partial(self):
        """Test converting partial response to dictionary."""
        response = JSONRPCResponse(id="123", result="partial data", partial=True)
        result = response.to_dict()
        
        expected = {
            "jsonrpc": "2.0",
            "id": "123",
            "partial": True,
            "data": "partial data"
        }
        assert result == expected
    
    def test_to_json(self):
        """Test converting response to JSON string."""
        response = JSONRPCResponse(id="123", result={"test": True})
        json_str = response.to_json()
        
        # Parse back to verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["id"] == "123"
        assert parsed["result"]["test"] is True


class TestJSONRPCError:
    """Test JSONRPCError class."""
    
    def test_create_error_basic(self):
        """Test creating basic error."""
        error = JSONRPCError.create_error(JSONRPCError.PARSE_ERROR)
        
        assert error["code"] == -32700
        assert error["message"] == "Parse error"
    
    def test_create_error_with_data(self):
        """Test creating error with additional data."""
        error = JSONRPCError.create_error(
            JSONRPCError.EXECUTION_ERROR, 
            {"details": "Function failed"}
        )
        
        assert error["code"] == -32000
        assert error["data"]["details"] == "Function failed"


class TestJSONRPCHandler:
    """Test JSONRPCHandler class."""
    
    def test_parse_request_valid(self):
        """Test parsing valid JSON-RPC request."""
        handler = JSONRPCHandler()
        json_line = '{"jsonrpc": "2.0", "method": "test", "id": "123"}'
        
        request = handler.parse_request(json_line)
        
        assert request is not None
        assert request.method == "test"
        assert request.id == "123"
    
    def test_parse_request_invalid_json(self):
        """Test parsing invalid JSON."""
        handler = JSONRPCHandler()
        json_line = '{"invalid": json}'
        
        request = handler.parse_request(json_line)
        
        assert request is None
    
    def test_parse_request_missing_method(self):
        """Test parsing request without method."""
        handler = JSONRPCHandler()
        json_line = '{"jsonrpc": "2.0", "id": "123"}'
        
        request = handler.parse_request(json_line)
        
        assert request is None
    
    def test_validate_request_valid(self):
        """Test validating valid request."""
        handler = JSONRPCHandler()
        request = JSONRPCRequest(method="test", id="123")
        
        error = handler.validate_request(request)
        
        assert error is None
    
    def test_validate_request_invalid_version(self):
        """Test validating request with invalid version."""
        handler = JSONRPCHandler()
        request = JSONRPCRequest(method="test", id="123", jsonrpc="1.0")
        
        error = handler.validate_request(request)
        
        assert error == JSONRPCError.INVALID_REQUEST
    
    def test_create_response(self):
        """Test creating response."""
        handler = JSONRPCHandler()
        
        response = handler.create_response("123", {"result": "success"})
        
        assert response.id == "123"
        assert response.result == {"result": "success"}
        assert response.error is None
    
    def test_create_error_response(self):
        """Test creating error response."""
        handler = JSONRPCHandler()
        
        response = handler.create_error_response(
            "123", 
            JSONRPCError.EXECUTION_ERROR,
            {"details": "test error"}
        )
        
        assert response.id == "123"
        assert response.error["code"] == -32000
        assert response.error["data"]["details"] == "test error"
