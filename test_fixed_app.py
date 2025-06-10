#!/usr/bin/env python
"""Test the fixed Gradio app creation."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def main():
    """Test the fixed app."""
    print("Testing fixed Gradio app...")
    
    try:
        # Test imports
        import gradio as gr
        print(f"✅ Gradio {gr.__version__} imported")
        
        from mcpy_lens.gradio_app.main import create_gradio_app
        print("✅ Main app module imported")
        
        # Test app creation
        print("\n🚀 Creating Gradio app...")
        app = create_gradio_app()
        print(f"✅ App created successfully: {type(app)}")
        
        # Test that the app has the expected structure
        print("\n🔍 Checking app structure...")
        print(f"App title: {getattr(app, 'title', 'No title')}")
        
        # Check if we can access the blocks
        if hasattr(app, 'blocks'):
            print(f"✅ App has blocks: {len(app.blocks)} components")
        
        print("\n🎉 All tests passed! The app creation is fixed.")
        print("\nTo launch the web interface:")
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
