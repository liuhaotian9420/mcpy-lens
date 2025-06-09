#!/usr/bin/env python
"""Simple launcher for the Gradio web interface with better error handling."""

import sys
import os
from pathlib import Path
import logging

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def setup_logging():
    """Set up logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def test_imports():
    """Test that all required modules can be imported."""
    try:
        import gradio as gr
        print(f"✅ Gradio {gr.__version__} imported successfully")
        
        from mcpy_lens.gradio_app.main import create_gradio_app
        print("✅ Gradio app modules imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def launch_app():
    """Launch the Gradio application."""
    try:
        print("🚀 Creating Gradio application...")
        from mcpy_lens.gradio_app.main import create_gradio_app
        
        app = create_gradio_app()
        print("✅ Gradio application created successfully")
        
        print("🌐 Launching web interface...")
        print("📍 URL: http://localhost:7860")
        print("🔧 Backend should be running on: http://localhost:8090")
        print("⏹️  Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # Launch the app
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            debug=True,
            show_error=True,
            quiet=False,
            inbrowser=True  # Automatically open browser
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error launching app: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main entry point."""
    print("=" * 60)
    print("🔍 mcpy-lens Gradio Web Interface Launcher")
    print("=" * 60)
    
    # Set up logging
    setup_logging()
    
    # Test imports
    print("\n1. Testing imports...")
    if not test_imports():
        print("❌ Import test failed. Please check your installation.")
        return 1
    
    # Launch app
    print("\n2. Launching application...")
    if not launch_app():
        print("❌ Failed to launch application.")
        return 1
    
    print("\n✅ Application finished successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
