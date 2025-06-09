#!/usr/bin/env python
"""Test script to verify the basic Gradio app structure without running it."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def test_imports():
    """Test that all our modules can be imported."""
    try:
        # Test API client
        from mcpy_lens.gradio_app.api_client import APIClient, get_api_client
        print("✅ API client imports successfully")
        
        # Test common components
        from mcpy_lens.gradio_app.components.common import (
            format_json_display, create_status_badge, safe_get_nested
        )
        print("✅ Common components import successfully")
        
        # Test file management interface
        from mcpy_lens.gradio_app.interfaces.file_management import create_file_management_interface
        print("✅ File management interface imports successfully")
        
        # Test service config interface
        from mcpy_lens.gradio_app.interfaces.service_config import create_service_config_interface
        print("✅ Service config interface imports successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_api_client():
    """Test API client functionality."""
    try:
        from mcpy_lens.gradio_app.api_client import APIClient
        
        # Create client (don't actually connect)
        client = APIClient("http://localhost:8090")
        print("✅ API client can be instantiated")
        
        # Test utility functions
        from mcpy_lens.gradio_app.components.common import (
            format_json_display, create_status_badge, format_file_size
        )
        
        # Test format functions
        test_data = {"test": "data", "number": 42}
        formatted = format_json_display(test_data)
        assert '"test": "data"' in formatted
        print("✅ JSON formatting works")
        
        # Test status badge
        badge = create_status_badge("active")
        assert "🟢" in badge
        print("✅ Status badge creation works")
        
        # Test file size formatting
        size = format_file_size(1024)
        assert "1.0 KB" == size
        print("✅ File size formatting works")
        
        return True
        
    except Exception as e:
        print(f"❌ API client test error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing mcpy-lens Gradio app structure...")
    print("=" * 50)
    
    success = True
    
    # Test imports
    print("\n1. Testing imports...")
    success &= test_imports()
    
    # Test API client
    print("\n2. Testing API client...")
    success &= test_api_client()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! The Gradio app structure is ready.")
        print("\nNext steps:")
        print("1. Install Gradio: pip install gradio")
        print("2. Start FastAPI backend: python run.py")
        print("3. Start Gradio frontend: python run_gradio.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
