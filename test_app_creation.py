#!/usr/bin/env python
"""Test script to verify the Gradio app can be created successfully."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def main():
    """Test app creation."""
    print("Testing Gradio app creation...")
    
    try:
        # Test imports
        import gradio as gr
        print(f"✅ Gradio {gr.__version__} imported")
        
        from mcpy_lens.gradio_app.api_client import APIClient
        print("✅ API client imported")
        
        from mcpy_lens.gradio_app.components.common import create_status_badge
        print("✅ Common components imported")
        
        from mcpy_lens.gradio_app.interfaces.file_management import create_file_management_interface
        print("✅ File management interface imported")
        
        from mcpy_lens.gradio_app.interfaces.service_config import create_service_config_interface
        print("✅ Service config interface imported")
        
        from mcpy_lens.gradio_app.interfaces.service_management import create_service_management_interface
        print("✅ Service management interface imported")
        
        from mcpy_lens.gradio_app.interfaces.service_testing import create_service_testing_interface
        print("✅ Service testing interface imported")
        
        from mcpy_lens.gradio_app.main import create_gradio_app
        print("✅ Main app module imported")
        
        # Test app creation
        print("\nCreating Gradio app...")
        app = create_gradio_app()
        print(f"✅ App created successfully: {type(app)}")
        
        # Test basic functionality
        status_badge = create_status_badge("active")
        print(f"✅ Status badge test: {status_badge}")
        
        print("\n🎉 All tests passed! The Gradio app is ready to launch.")
        print("\nTo start the web interface:")
        print("1. Start FastAPI backend: python run.py")
        print("2. Start Gradio frontend: python launch_gradio.py")
        print("3. Open http://localhost:7860 in your browser")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
