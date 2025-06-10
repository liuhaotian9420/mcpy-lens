"""File management interface for uploading and managing Python scripts."""

import gradio as gr
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
import logging
import tempfile
import os

from ..api_client import get_api_client
from ..components.common import (
    create_error_display, create_success_display, create_info_display,
    format_json_display, create_status_badge, create_refresh_button,
    create_action_button, format_file_size, format_timestamp,
    create_empty_state_message, create_loading_message
)

logger = logging.getLogger(__name__)


def create_file_management_interface() -> gr.Tab:
    """Create the file management interface tab.
    
    Returns:
        Gradio Tab component with file management interface
    """
    with gr.Tab("📁 File Management") as tab:
        gr.Markdown("## Upload and Manage Python Scripts")
        gr.Markdown("Upload Python files to create MCP services and manage existing scripts.")
        
        with gr.Row():
            with gr.Column(scale=1):
                # File upload section
                gr.Markdown("### Upload New Script")
                file_upload = gr.File(
                    label="Select Python File",
                    file_types=[".py"],
                    file_count="single"
                )
                upload_btn = create_action_button("📤 Upload Script")
                upload_status = gr.Markdown("")
                
            with gr.Column(scale=2):
                # File preview section
                gr.Markdown("### File Preview")
                file_preview = gr.Code(
                    label="Script Content",
                    language="python",
                    interactive=False,
                    lines=15
                )
        
        # Script metadata section
        gr.Markdown("### Script Metadata")
        metadata_display = gr.JSON(label="Script Information")

        # Function discovery section
        gr.Markdown("### Discovered Functions")
        discover_btn = create_action_button("🔍 Discover Functions", "secondary")
        functions_display = gr.JSON(label="Functions", value={"message": "Select a script and click 'Discover Functions' to see available functions"})
        
        # Scripts list section
        with gr.Row():
            gr.Markdown("### Uploaded Scripts")
            refresh_btn = create_refresh_button("🔄 Refresh List")
        
        scripts_table = gr.DataFrame(
            headers=["ID", "Filename", "Status", "Functions", "Size", "Upload Date", "Actions"],
            datatype=["str", "str", "str", "str", "str", "str", "str"],
            interactive=True,
            wrap=True
        )
        
        # Script actions
        with gr.Row():
            with gr.Column():
                selected_script_id = gr.Textbox(
                    label="Selected Script ID",
                    placeholder="Enter script ID or select from table",
                    interactive=True
                )
            with gr.Column():
                view_btn = create_action_button("👁️ View Details", "secondary")
                delete_btn = create_action_button("🗑️ Delete Script", "stop")
        
        # Action results
        action_status = gr.Markdown("")
        
        # Event handlers
        def handle_file_upload(file) -> Tuple[str, str, Dict[str, Any]]:
            """Handle file upload."""
            if file is None:
                return "❌ No file selected", "", {}
            
            try:
                api_client = get_api_client()
                result = api_client.upload_script(file.name)
                
                if "error" in result:
                    return f"❌ Upload failed: {result['error']}", "", {}
                
                # Read file content for preview
                try:
                    with open(file.name, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading file: {e}"
                
                success_msg = f"✅ Script uploaded successfully!\n\n**Script ID**: {result.get('script_id', 'Unknown')}"
                return success_msg, content, result
                
            except Exception as e:
                logger.error(f"Upload error: {e}")
                return f"❌ Upload failed: {str(e)}", "", {}
        
        def load_scripts_list() -> pd.DataFrame:
            """Load and format scripts list."""
            try:
                api_client = get_api_client()
                result = api_client.list_scripts(limit=100)
                
                if "error" in result:
                    logger.error(f"Failed to load scripts: {result['error']}")
                    return pd.DataFrame(columns=["ID", "Filename", "Status", "Functions", "Size", "Upload Date", "Actions"])
                
                scripts = result.get("scripts", [])
                if not scripts:
                    return pd.DataFrame(columns=["ID", "Filename", "Status", "Functions", "Size", "Upload Date", "Actions"])
                
                # Format data for table
                table_data = []
                for script in scripts:
                    functions = script.get("functions", [])
                    function_count = len(functions) if functions else 0

                    table_data.append([
                        script.get("script_id", ""),  # Full ID for selection
                        script.get("filename", "Unknown"),
                        create_status_badge(script.get("status", "unknown")),
                        f"{function_count} functions",
                        format_file_size(script.get("file_size", 0)),
                        format_timestamp(script.get("created_at", "")),
                        "View | Delete"
                    ])
                
                return pd.DataFrame(
                    table_data,
                    columns=["ID", "Filename", "Status", "Functions", "Size", "Upload Date", "Actions"]
                )
                
            except Exception as e:
                logger.error(f"Error loading scripts: {e}")
                return pd.DataFrame(columns=["ID", "Filename", "Status", "Functions", "Size", "Upload Date", "Actions"])
        
        def handle_view_script(script_id: str) -> Tuple[str, Dict[str, Any]]:
            """Handle viewing script details."""
            if not script_id.strip():
                return "❌ Please enter a script ID", {}
            
            try:
                api_client = get_api_client()
                result = api_client.get_script(script_id)
                
                if "error" in result:
                    return f"❌ Failed to load script: {result['error']}", {}
                
                return f"✅ Script details loaded for ID: {script_id}", result
                
            except Exception as e:
                logger.error(f"Error viewing script: {e}")
                return f"❌ Error: {str(e)}", {}
        
        def handle_delete_script(script_id: str) -> Tuple[str, pd.DataFrame]:
            """Handle script deletion."""
            if not script_id.strip():
                return "❌ Please enter a script ID", load_scripts_list()

            try:
                api_client = get_api_client()
                result = api_client.delete_script(script_id)

                if "error" in result:
                    return f"❌ Failed to delete script: {result['error']}", load_scripts_list()

                return f"✅ Script {script_id} deleted successfully", load_scripts_list()

            except Exception as e:
                logger.error(f"Error deleting script: {e}")
                return f"❌ Error: {str(e)}", load_scripts_list()

        def handle_discover_functions(script_id: str) -> Dict[str, Any]:
            """Handle function discovery for a script."""
            if not script_id.strip():
                return {"error": "Please enter a script ID"}

            try:
                api_client = get_api_client()
                result = api_client.discover_tools(script_id)

                if "error" in result:
                    return {"error": f"Failed to discover functions: {result['error']}"}

                # Format the response for better display
                tools = result.get("tools", [])
                if not tools:
                    return {"message": "No functions found in this script"}

                formatted_result = {
                    "script_id": result.get("file_id", script_id),
                    "total_functions": result.get("total", 0),
                    "discovery_time": result.get("discovery_time", ""),
                    "functions": []
                }

                for tool in tools:
                    formatted_result["functions"].append({
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {}),
                        "return_type": tool.get("return_type", "")
                    })

                return formatted_result

            except Exception as e:
                logger.error(f"Error discovering functions: {e}")
                return {"error": f"Error: {str(e)}"}

        def handle_table_select(evt: gr.SelectData) -> str:
            """Handle table row selection."""
            if evt.index is not None and len(evt.index) >= 2:
                # Get the script ID from the first column
                return evt.value if evt.index[1] == 0 else ""
            return ""
        
        # Wire up event handlers
        upload_btn.click(
            fn=handle_file_upload,
            inputs=[file_upload],
            outputs=[upload_status, file_preview, metadata_display]
        )
        
        refresh_btn.click(
            fn=load_scripts_list,
            outputs=[scripts_table]
        )
        
        view_btn.click(
            fn=handle_view_script,
            inputs=[selected_script_id],
            outputs=[action_status, metadata_display]
        )
        
        delete_btn.click(
            fn=handle_delete_script,
            inputs=[selected_script_id],
            outputs=[action_status, scripts_table]
        )

        discover_btn.click(
            fn=handle_discover_functions,
            inputs=[selected_script_id],
            outputs=[functions_display]
        )

        scripts_table.select(
            fn=handle_table_select,
            outputs=[selected_script_id]
        )

        # Note: Users can click the refresh button to load initial data

    return tab
