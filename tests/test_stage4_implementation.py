#!/usr/bin/env python3
"""
Test script for Stage 4 wrapper implementation.
"""

import sys
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def test_json_rpc_handler():
    """Test JSON-RPC protocol handling."""
    print("🔍 Testing JSON-RPC handler...")
    
    try:
        from mcpy_lens.wrapper.json_rpc import JSONRPCHandler, JSONRPCRequest
        
        handler = JSONRPCHandler()
        
        # Test parsing valid request
        json_line = '{"jsonrpc": "2.0", "method": "listtools", "id": "123"}'
        request = handler.parse_request(json_line)
        
        assert request is not None
        assert request.method == "listtools"
        assert request.id == "123"
        
        # Test creating response
        response = handler.create_response("123", {"tools": []})
        json_str = response.to_json()
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["id"] == "123"
        
        print("✅ JSON-RPC handler working correctly")
        return True
        
    except Exception as e:
        print(f"❌ JSON-RPC handler test failed: {e}")
        return False

def test_wrapper_config():
    """Test wrapper configuration."""
    print("\n🔧 Testing wrapper configuration...")
    
    try:
        from mcpy_lens.wrapper.config import WrapperConfig
        
        # Test default config
        config = WrapperConfig()
        assert config.max_execution_time == 300
        assert config.python_executable == "python"
        
        # Test environment creation
        env = config.get_subprocess_env()
        assert isinstance(env, dict)
        
        print("✅ Wrapper configuration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Wrapper configuration test failed: {e}")
        return False

def test_script_wrapper_creation():
    """Test script wrapper creation."""
    print("\n🎁 Testing script wrapper creation...")
    
    try:
        from mcpy_lens.wrapper.script_wrapper import ScriptWrapper
        from mcpy_lens.wrapper.config import WrapperConfig
        
        # Create temporary script and metadata files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
            script_file.write('''
def hello_world(name: str = "World") -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello_world())
''')
            script_path = Path(script_file.name)
        
        # Create metadata file
        metadata = {
            "script_info": {
                "script_id": "test-123",
                "filename": "test.py"
            },
            "tools": [
                {
                    "name": "hello_world",
                    "description": "Say hello to someone.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "default": "World"}
                        }
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "result": {"type": "string"}
                        }
                    }
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as metadata_file:
            json.dump(metadata, metadata_file)
            metadata_path = Path(metadata_file.name)
        
        try:
            # Create wrapper
            config = WrapperConfig()
            wrapper = ScriptWrapper(
                script_path=script_path,
                metadata_path=metadata_path,
                config=config
            )
            
            # Verify wrapper was created
            assert wrapper.script_path == script_path
            assert wrapper.metadata_path == metadata_path
            assert len(wrapper.metadata["tools"]) == 1
            
            print("✅ Script wrapper creation working correctly")
            return True
            
        finally:
            # Clean up
            script_path.unlink()
            metadata_path.unlink()
        
    except Exception as e:
        print(f"❌ Script wrapper creation test failed: {e}")
        return False

def test_wrapper_generator():
    """Test wrapper generator."""
    print("\n🏗️ Testing wrapper generator...")
    
    try:
        from mcpy_lens.wrapper.generator import WrapperGenerator
        from mcpy_lens.wrapper.config import WrapperConfig
        from mcpy_lens.models import ScriptMetadata, FunctionInfo
        from datetime import datetime
        
        # Create test script metadata
        metadata = ScriptMetadata(
            script_id="test-456",
            filename="test_script.py",
            upload_time=datetime.now(),
            file_size=1024,
            functions=[
                FunctionInfo(
                    name="test_function",
                    description="A test function",
                    parameters={"arg1": "str"},
                    return_type="str",
                    line_number=1
                )
            ],
            imports=[],
            dependencies=[],
            validation_status="passed",
            security_status="safe"
        )
        
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
            script_file.write('''
def test_function(arg1: str) -> str:
    """A test function."""
    return f"Processed: {arg1}"
''')
            script_path = Path(script_file.name)
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            try:
                generator = WrapperGenerator(WrapperConfig())
                
                # Test metadata creation
                tool_metadata = generator._create_tool_metadata(metadata, ["test_function"])
                assert len(tool_metadata["tools"]) == 1
                assert tool_metadata["tools"][0]["name"] == "test_function"
                
                print("✅ Wrapper generator working correctly")
                return True
                
            finally:
                script_path.unlink()
        
    except Exception as e:
        print(f"❌ Wrapper generator test failed: {e}")
        return False

def main():
    """Run all Stage 4 tests."""
    print("🚀 Stage 4 Wrapper Implementation Tests")
    print("=" * 50)
    
    tests = [
        test_json_rpc_handler,
        test_wrapper_config,
        test_script_wrapper_creation,
        test_wrapper_generator,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Stage 4 wrapper implementation tests passed!")
        print("\n✨ Stage 4 core functionality is working!")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
