#!/usr/bin/env python3
"""
Verification script for Stage 3 implementation.
Tests the implementation without requiring a running server.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def test_imports():
    """Test that all new imports work correctly."""
    print("🔍 Testing imports...")
    
    try:
        # Test new model imports
        from mcpy_lens.models import (
            FunctionSelectionRequest,
            FunctionSelectionResponse,
            ScriptParameter,
            ScriptParametersRequest,
            ScriptParametersResponse,
            CLIWrapperRequest,
            CLIWrapperResponse
        )
        print("✅ New models imported successfully")
        
        # Test file service imports
        from mcpy_lens.file_service import FileService
        print("✅ FileService imported successfully")
        
        # Test file routes imports
        from mcpy_lens.file_routes import file_router
        print("✅ File routes imported successfully")
        
        # Test app imports
        from mcpy_lens.app import fastapi_app
        print("✅ FastAPI app imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_model_creation():
    """Test that new models can be created and validated."""
    print("\n🏗️ Testing model creation...")
    
    try:
        from mcpy_lens.models import (
            FunctionSelectionRequest,
            ScriptParameter,
            ScriptParametersRequest,
            CLIWrapperRequest
        )
        
        # Test FunctionSelectionRequest
        selection_req = FunctionSelectionRequest(
            selected_functions=["func1", "func2"],
            metadata={"test": "data"}
        )
        print("✅ FunctionSelectionRequest created successfully")
        
        # Test ScriptParameter
        param = ScriptParameter(
            name="test_param",
            type="str",
            description="Test parameter",
            required=True
        )
        print("✅ ScriptParameter created successfully")
        
        # Test ScriptParametersRequest
        params_req = ScriptParametersRequest(
            parameters=[param]
        )
        print("✅ ScriptParametersRequest created successfully")
        
        # Test CLIWrapperRequest
        wrapper_req = CLIWrapperRequest(
            wrapper_name="test_wrapper",
            description="Test wrapper"
        )
        print("✅ CLIWrapperRequest created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Model creation failed: {e}")
        return False

def test_file_service_methods():
    """Test that FileService has the new methods."""
    print("\n🔧 Testing FileService methods...")
    
    try:
        from mcpy_lens.file_service import FileService
        
        # Create FileService instance
        fs = FileService()
        print("✅ FileService instantiated")
        
        # Check that new methods exist
        required_methods = [
            'select_functions_for_tools',
            'get_selected_functions',
            'configure_script_parameters',
            'get_script_parameters',
            'generate_whole_file_cli_wrapper'
        ]
        
        for method_name in required_methods:
            if hasattr(fs, method_name):
                print(f"✅ Method {method_name} exists")
            else:
                print(f"❌ Method {method_name} missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ FileService method test failed: {e}")
        return False

def test_api_routes():
    """Test that new API routes are registered."""
    print("\n🛣️ Testing API routes...")
    
    try:
        from mcpy_lens.app import fastapi_app
        
        # Get all routes
        routes = [route.path for route in fastapi_app.routes]
        
        # Check for new routes
        required_routes = [
            '/api/v1/scripts/{script_id}/functions/select',
            '/api/v1/scripts/{script_id}/functions/selected',
            '/api/v1/scripts/{script_id}/cli_params',
            '/api/v1/scripts/{script_id}/generate_cli_wrapper'
        ]
        
        for route_path in required_routes:
            if route_path in routes:
                print(f"✅ Route {route_path} registered")
            else:
                print(f"❌ Route {route_path} missing")
                return False
        
        print(f"✅ Total routes registered: {len(routes)}")
        return True
    except Exception as e:
        print(f"❌ API routes test failed: {e}")
        return False

async def test_wrapper_generation_logic():
    """Test the CLI wrapper generation logic."""
    print("\n🎁 Testing wrapper generation logic...")

    try:
        from mcpy_lens.file_service import FileService
        from mcpy_lens.models import ScriptParameter
        from pathlib import Path

        fs = FileService()

        # Create a test script
        test_script_content = '''def test_func():
    print("Hello World")

if __name__ == "__main__":
    test_func()
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_content)
            test_script_path = Path(f.name)

        try:
            # Test parameters
            params = [
                ScriptParameter(
                    name="verbose",
                    type="bool",
                    description="Enable verbose output",
                    required=False,
                    default_value=False
                )
            ]

            # Test wrapper generation method exists and can be called
            from mcpy_lens.models import CLIWrapperRequest
            wrapper_req = CLIWrapperRequest(
                wrapper_name="test",
                description="Test wrapper"
            )

            # This should not fail with import/method errors
            wrapper_content = await fs._generate_whole_file_wrapper_content(
                test_script_path, params, wrapper_req
            )

            if "typer" in wrapper_content and "def main" in wrapper_content:
                print("✅ Wrapper content generation works")
                return True
            else:
                print("❌ Wrapper content doesn't contain expected elements")
                return False

        finally:
            # Clean up
            if test_script_path.exists():
                test_script_path.unlink()

    except Exception as e:
        print(f"❌ Wrapper generation test failed: {e}")
        return False

async def run_async_tests():
    """Run tests that require async."""
    return await test_wrapper_generation_logic()

def main():
    """Run all verification tests."""
    print("🚀 Stage 3 Implementation Verification")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_model_creation,
        test_file_service_methods,
        test_api_routes,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    # Run async test
    import asyncio
    try:
        if asyncio.run(run_async_tests()):
            passed += 1
        total += 1
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        total += 1
    
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Stage 3 implementation tests passed!")
        print("\n✨ Stage 3 is complete and ready for use!")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
