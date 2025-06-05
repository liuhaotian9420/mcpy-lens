#!/usr/bin/env python3
"""
Simple test runner for wrapper unit tests without pytest.
"""

import sys
import json

# Add src to path
sys.path.insert(0, 'src')

def test_json_rpc_request():
    """Test JSONRPCRequest class."""
    from mcpy_lens.wrapper.json_rpc import JSONRPCRequest
    
    # Test from_dict_basic
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
    
    # Test from_dict_with_params
    data = {
        "jsonrpc": "2.0",
        "method": "test_method",
        "params": {"arg1": "value1"},
        "id": "123"
    }
    request = JSONRPCRequest.from_dict(data)
    
    assert request.params == {"arg1": "value1"}
    
    print("✅ JSONRPCRequest tests passed")

def test_json_rpc_response():
    """Test JSONRPCResponse class."""
    from mcpy_lens.wrapper.json_rpc import JSONRPCResponse
    
    # Test to_dict_success
    response = JSONRPCResponse(id="123", result={"data": "test"})
    result = response.to_dict()
    
    expected = {
        "jsonrpc": "2.0",
        "id": "123",
        "result": {"data": "test"}
    }
    assert result == expected
    
    # Test to_dict_error
    error = {"code": -32000, "message": "Test error"}
    response = JSONRPCResponse(id="123", error=error)
    result = response.to_dict()
    
    expected = {
        "jsonrpc": "2.0",
        "id": "123",
        "error": error
    }
    assert result == expected
    
    # Test to_dict_partial
    response = JSONRPCResponse(id="123", result="partial data", partial=True)
    result = response.to_dict()
    
    expected = {
        "jsonrpc": "2.0",
        "id": "123",
        "partial": True,
        "data": "partial data"
    }
    assert result == expected
    
    # Test to_json
    response = JSONRPCResponse(id="123", result={"test": True})
    json_str = response.to_json()
    
    # Parse back to verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed["id"] == "123"
    assert parsed["result"]["test"] is True
    
    print("✅ JSONRPCResponse tests passed")

def test_json_rpc_error():
    """Test JSONRPCError class."""
    from mcpy_lens.wrapper.json_rpc import JSONRPCError
    
    # Test create_error_basic
    error = JSONRPCError.create_error(JSONRPCError.PARSE_ERROR)
    
    assert error["code"] == -32700
    assert error["message"] == "Parse error"
    
    # Test create_error_with_data
    error = JSONRPCError.create_error(
        JSONRPCError.EXECUTION_ERROR, 
        {"details": "Function failed"}
    )
    
    assert error["code"] == -32000
    assert error["data"]["details"] == "Function failed"
    
    print("✅ JSONRPCError tests passed")

def test_json_rpc_handler():
    """Test JSONRPCHandler class."""
    from mcpy_lens.wrapper.json_rpc import JSONRPCHandler, JSONRPCRequest, JSONRPCError
    
    handler = JSONRPCHandler()
    
    # Test parse_request_valid
    json_line = '{"jsonrpc": "2.0", "method": "test", "id": "123"}'
    
    request = handler.parse_request(json_line)
    
    assert request is not None
    assert request.method == "test"
    assert request.id == "123"
    
    # Test parse_request_invalid_json
    json_line = '{"invalid": json}'
    
    request = handler.parse_request(json_line)
    
    assert request is None
    
    # Test parse_request_missing_method
    json_line = '{"jsonrpc": "2.0", "id": "123"}'
    
    request = handler.parse_request(json_line)
    
    assert request is None
    
    # Test validate_request_valid
    request = JSONRPCRequest(method="test", id="123")
    
    error = handler.validate_request(request)
    
    assert error is None
    
    # Test validate_request_invalid_version
    request = JSONRPCRequest(method="test", id="123", jsonrpc="1.0")
    
    error = handler.validate_request(request)
    
    assert error == JSONRPCError.INVALID_REQUEST
    
    # Test create_response
    response = handler.create_response("123", {"result": "success"})
    
    assert response.id == "123"
    assert response.result == {"result": "success"}
    assert response.error is None
    
    # Test create_error_response
    response = handler.create_error_response(
        "123", 
        JSONRPCError.EXECUTION_ERROR,
        {"details": "test error"}
    )
    
    assert response.id == "123"
    assert response.error["code"] == -32000
    assert response.error["data"]["details"] == "test error"
    
    print("✅ JSONRPCHandler tests passed")

def test_wrapper_config():
    """Test WrapperConfig class."""
    import os
    from mcpy_lens.wrapper.config import WrapperConfig
    
    # Test default_values
    config = WrapperConfig()
    
    assert config.max_execution_time == 300
    assert config.max_memory_mb == 512
    assert config.max_output_lines == 10000
    assert config.max_concurrent_processes == 8
    assert config.python_executable == "python"
    assert config.working_directory is None
    assert config.stream_buffer_size == 1024
    assert config.stream_flush_interval == 0.1
    assert config.allow_network_access is True
    assert config.allow_file_write is True
    
    # Test get_subprocess_env_default
    config = WrapperConfig()
    env = config.get_subprocess_env()
    
    # Should include current environment
    assert "PATH" in env or "Path" in env  # Windows uses "Path"
    
    # Should not have proxy restrictions by default
    assert "NO_PROXY" not in env
    
    # Test get_subprocess_env_no_network
    config = WrapperConfig(allow_network_access=False)
    env = config.get_subprocess_env()
    
    # Should have proxy restrictions
    assert env["NO_PROXY"] == "*"
    assert env["no_proxy"] == "*"
    
    print("✅ WrapperConfig tests passed")

def main():
    """Run all unit tests."""
    print("🧪 Running Unit Tests for Stage 4 Wrapper Implementation")
    print("=" * 60)
    
    tests = [
        test_json_rpc_request,
        test_json_rpc_response,
        test_json_rpc_error,
        test_json_rpc_handler,
        test_wrapper_config,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
        print()
    
    print("=" * 60)
    print(f"📊 Unit Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All unit tests passed!")
        return True
    else:
        print("❌ Some unit tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
