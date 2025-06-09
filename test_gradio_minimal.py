#!/usr/bin/env python
"""Minimal Gradio test to verify installation and basic functionality."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def test_gradio_import():
    """Test that Gradio can be imported and basic functionality works."""
    try:
        import gradio as gr
        print(f"✅ Gradio imported successfully, version: {gr.__version__}")
        
        # Test basic Gradio functionality
        def hello(name):
            return f"Hello {name}!"
        
        # Create a simple interface
        demo = gr.Interface(
            fn=hello,
            inputs=gr.Textbox(placeholder="Enter your name"),
            outputs=gr.Textbox(),
            title="Test Gradio Interface"
        )
        
        print("✅ Gradio interface created successfully")
        
        # Test launch with share=False and show_error=True
        print("🚀 Launching Gradio interface...")
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            debug=True,
            show_error=True,
            quiet=False,
            prevent_thread_lock=True  # This allows the script to continue
        )
        
        print("✅ Gradio interface launched successfully!")
        print("🌐 Open http://localhost:7860 in your browser to test")
        
        # Keep the server running for a bit
        import time
        print("⏳ Server running for 30 seconds...")
        time.sleep(30)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the minimal Gradio test."""
    print("Testing minimal Gradio functionality...")
    print("=" * 50)
    
    success = test_gradio_import()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Minimal Gradio test completed successfully!")
    else:
        print("❌ Gradio test failed.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
