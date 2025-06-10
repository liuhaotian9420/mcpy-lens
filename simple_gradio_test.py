#!/usr/bin/env python
"""Simple Gradio test to verify everything works."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

import gradio as gr

def test_backend_connection():
    """Test connection to FastAPI backend."""
    try:
        import httpx
        response = httpx.get("http://localhost:8090/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            return f"✅ Backend Connected: {data.get('status', 'unknown')}"
        else:
            return f"⚠️ Backend responded with status {response.status_code}"
    except Exception as e:
        return f"❌ Backend connection failed: {str(e)}"

def create_simple_app():
    """Create a simple Gradio app to test functionality."""
    
    with gr.Blocks(
        title="mcpy-lens Web Interface (Test)",
        theme=gr.themes.Soft()
    ) as app:
        
        gr.Markdown("# 🔍 mcpy-lens Web Interface")
        gr.Markdown("**Test Version** - Verifying Gradio functionality")
        
        # Backend status
        with gr.Row():
            status_display = gr.Markdown("Checking backend status...")
            refresh_btn = gr.Button("🔄 Refresh Status", variant="secondary")
        
        # Simple test interface
        with gr.Tab("🧪 Test Interface"):
            gr.Markdown("## Test Basic Functionality")
            
            with gr.Row():
                test_input = gr.Textbox(label="Test Input", placeholder="Enter some text...")
                test_output = gr.Textbox(label="Test Output", interactive=False)
            
            test_btn = gr.Button("🚀 Test Function", variant="primary")
            
            def test_function(input_text):
                if input_text:
                    return f"✅ Received: {input_text}"
                else:
                    return "❌ No input provided"
            
            test_btn.click(
                fn=test_function,
                inputs=[test_input],
                outputs=[test_output]
            )
        
        with gr.Tab("📋 Backend Status"):
            gr.Markdown("## FastAPI Backend Connection")
            backend_details = gr.JSON(label="Backend Response")
            
            def get_backend_details():
                try:
                    import httpx
                    response = httpx.get("http://localhost:8090/health", timeout=5.0)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        return {"error": f"HTTP {response.status_code}"}
                except Exception as e:
                    return {"error": str(e)}
            
            check_backend_btn = gr.Button("🔍 Check Backend Details")
            check_backend_btn.click(
                fn=get_backend_details,
                outputs=[backend_details]
            )
        
        with gr.Tab("❓ Help"):
            gr.Markdown("""
            ## Simple Test Interface
            
            This is a simplified version of the mcpy-lens web interface for testing purposes.
            
            ### What to test:
            1. **Test Interface**: Enter text and click "Test Function" to verify basic Gradio functionality
            2. **Backend Status**: Check if the FastAPI backend is running on port 8090
            
            ### Full Interface:
            If this test works, the full interface should work too. The full interface includes:
            - File upload and management
            - Service configuration
            - Service management and monitoring
            - Interactive tool testing
            
            ### Troubleshooting:
            - Make sure FastAPI backend is running: `python run.py`
            - Check that port 7860 is available
            - Verify Gradio installation: `python -c "import gradio; print(gradio.__version__)"`
            """)
        
        # Wire up refresh button
        refresh_btn.click(
            fn=test_backend_connection,
            outputs=[status_display]
        )
        
        # Load initial status
        app.load(
            fn=test_backend_connection,
            outputs=[status_display]
        )
    
    return app

def main():
    """Main function to run the simple test app."""
    print("🚀 Starting simple Gradio test...")
    
    try:
        app = create_simple_app()
        print("✅ Simple app created successfully")
        
        print("🌐 Launching on http://localhost:7860")
        print("⏹️  Press Ctrl+C to stop")
        
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            debug=True,
            show_error=True,
            inbrowser=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
