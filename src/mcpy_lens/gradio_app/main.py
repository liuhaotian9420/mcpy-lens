"""Main Gradio application for mcpy-lens web interface."""

import gradio as gr
import logging
from typing import Optional
import os
import sys

# Add the src directory to Python path for imports
src_dir = os.path.join(os.path.dirname(__file__), "..", "..")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from .api_client import get_api_client, close_api_client
from .interfaces.file_management import create_file_management_interface
from .interfaces.service_config import create_service_config_interface
from .interfaces.service_management import create_service_management_interface
from .interfaces.service_testing import create_service_testing_interface

logger = logging.getLogger(__name__)


def create_gradio_app() -> gr.Blocks:
    """Create the main Gradio application.
    
    Returns:
        Gradio Blocks application
    """
    # Custom CSS for better styling
    custom_css = """
    .error-message {
        color: #dc3545 !important;
        background-color: #f8d7da !important;
        border: 1px solid #f5c6cb !important;
        padding: 10px !important;
        border-radius: 5px !important;
        margin: 10px 0 !important;
    }
    
    .success-message {
        color: #155724 !important;
        background-color: #d4edda !important;
        border: 1px solid #c3e6cb !important;
        padding: 10px !important;
        border-radius: 5px !important;
        margin: 10px 0 !important;
    }
    
    .info-message {
        color: #0c5460 !important;
        background-color: #d1ecf1 !important;
        border: 1px solid #bee5eb !important;
        padding: 10px !important;
        border-radius: 5px !important;
        margin: 10px 0 !important;
    }
    
    .help-text {
        color: #6c757d !important;
        font-style: italic !important;
        font-size: 0.9em !important;
        margin: 5px 0 !important;
    }
    
    .refresh-button {
        min-width: 120px !important;
    }
    
    .action-button {
        min-width: 140px !important;
    }
    
    .gradio-container {
        max-width: 1200px !important;
        margin: 0 auto !important;
    }
    
    .tab-nav {
        background-color: #f8f9fa !important;
        border-bottom: 2px solid #dee2e6 !important;
    }
    """
    
    with gr.Blocks(
        title="mcpy-lens Web Interface",
        css=custom_css,
        theme=gr.themes.Soft()
    ) as app:
        # Header
        gr.Markdown(
            """
            # 🔍 mcpy-lens Web Interface
            
            **Upload Python scripts and create MCP services with ease**
            
            This interface allows you to upload Python files, configure them as MCP (Model Context Protocol) services, 
            and manage their lifecycle through an intuitive web interface.
            """,
            elem_classes=["header"]
        )
        
        # Backend status check
        def check_backend_status() -> str:
            """Check if the FastAPI backend is accessible."""
            try:
                api_client = get_api_client()
                health = api_client.health_check()

                if health.get("status") == "healthy":
                    return "✅ **Backend Status**: Connected to FastAPI backend"
                else:
                    return f"⚠️ **Backend Status**: {health.get('message', 'Unknown status')}"
            except Exception as e:
                return f"❌ **Backend Status**: Cannot connect to FastAPI backend - {str(e)}\n\n**Note**: Start the FastAPI backend with `python run.py` in another terminal."
        
        # Status display
        backend_status = gr.Markdown(check_backend_status())
        
        # Refresh status button
        with gr.Row():
            refresh_status_btn = gr.Button("🔄 Refresh Backend Status", variant="secondary", size="sm")
        
        refresh_status_btn.click(
            fn=check_backend_status,
            outputs=[backend_status]
        )
        
        # Main interface tabs
        with gr.Tabs():
            # File Management Tab
            file_tab = create_file_management_interface()
            
            # Service Configuration Tab
            config_tab = create_service_config_interface()

            # Service Management Tab
            mgmt_tab = create_service_management_interface()

            # Service Testing Tab
            test_tab = create_service_testing_interface()
            
            # Configuration Management Tab (placeholder for now)
            with gr.Tab("📝 Configuration") as config_mgmt_tab:
                gr.Markdown("## Configuration Management")
                gr.Markdown("*Coming soon - manage service configurations*")
                
                # Placeholder content
                gr.Markdown("""
                This tab will include:
                - JSON/YAML configuration editor
                - Configuration templates
                - Import/export functionality
                - Configuration validation
                """)
            
            # Help Tab
            with gr.Tab("❓ Help") as help_tab:
                gr.Markdown("""
                ## Getting Started
                
                ### 1. Upload a Python Script
                - Go to the **File Management** tab
                - Click "Select Python File" and choose a .py file
                - Click "Upload Script" to upload and analyze the file
                
                ### 2. Configure a Service
                - Go to the **Service Configuration** tab
                - Select your uploaded script from the dropdown
                - Choose hosting mode (Function or Executable)
                - Configure the service settings
                - Click "Create Service" to deploy
                
                ### 3. Manage Services
                - Use the **Service Management** tab to monitor and control services
                - View real-time status, logs, and performance metrics
                - Start, stop, or restart services as needed
                
                ### 4. Test Services
                - Use the **Service Testing** tab to test your MCP tools
                - Fill in parameters and see real-time responses
                - Save and reuse test configurations
                
                ## About MCP (Model Context Protocol)
                
                MCP is a protocol that allows AI models to securely access external tools and data sources.
                This interface helps you convert Python scripts into MCP-compatible services that can be
                used by AI models and other applications.
                
                ## Support
                
                - **Backend API**: Running on http://localhost:8090
                - **Web Interface**: Running on http://localhost:7860
                - **Documentation**: Check the project README for detailed information
                """)
        
        # Footer
        gr.Markdown(
            """
            ---
            **mcpy-lens** - Convert Python scripts to MCP services | 
            [Documentation](https://github.com/liuhaotian9420/mcpy-lens) | 
            [Issues](https://github.com/liuhaotian9420/mcpy-lens/issues)
            """,
            elem_classes=["footer"]
        )
        
        # Load initial backend status
        app.load(
            fn=check_backend_status,
            outputs=[backend_status]
        )
    
    return app


def main():
    """Main entry point for the Gradio application."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting mcpy-lens Gradio web interface...")
    
    try:
        # Create and launch the Gradio app
        app = create_gradio_app()
        
        # Launch with custom settings
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            debug=True,
            show_error=True,
            quiet=False
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error running Gradio app: {e}")
        raise
    finally:
        # Clean up API client
        close_api_client()


if __name__ == "__main__":
    main()
