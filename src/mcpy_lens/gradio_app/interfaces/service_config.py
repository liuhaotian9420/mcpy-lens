"""Service configuration interface for creating and configuring MCP services."""

import gradio as gr
from typing import Any, Dict, List, Optional, Tuple
import logging
import json

from ..api_client import get_api_client
from ..components.common import (
    create_error_display, create_success_display, create_info_display,
    format_json_display, create_refresh_button, create_action_button,
    validate_json_input, create_help_text
)

logger = logging.getLogger(__name__)


def create_service_config_interface() -> gr.Tab:
    """Create the service configuration interface tab.
    
    Returns:
        Gradio Tab component with service configuration interface
    """
    with gr.Tab("⚙️ Service Configuration") as tab:
        gr.Markdown("## Create and Configure MCP Services")
        gr.Markdown("Configure how your Python scripts are exposed as MCP services.")
        
        # Step 1: Script Selection
        with gr.Group():
            gr.Markdown("### Step 1: Select Script")
            with gr.Row():
                script_dropdown = gr.Dropdown(
                    label="Select Script",
                    choices=[],
                    interactive=True,
                    allow_custom_value=False
                )
                refresh_scripts_btn = create_refresh_button("🔄 Refresh Scripts")
            
            script_info = gr.JSON(label="Script Information", visible=False)
        
        # Step 2: Service Configuration
        with gr.Group():
            gr.Markdown("### Step 2: Service Configuration")
            
            with gr.Row():
                service_name = gr.Textbox(
                    label="Service Name",
                    placeholder="Enter a unique service name",
                    interactive=True
                )
                service_description = gr.Textbox(
                    label="Service Description",
                    placeholder="Describe what this service does",
                    interactive=True
                )
            
            with gr.Row():
                hosting_mode = gr.Radio(
                    label="Hosting Mode",
                    choices=[
                        ("Function Mode", "function"),
                        ("Executable Mode", "executable")
                    ],
                    value="function",
                    info="Function mode exposes individual functions, Executable mode runs the entire script"
                )
                
                protocol = gr.Dropdown(
                    label="Protocol",
                    choices=[
                        ("STDIO", "stdio"),
                        ("SSE/HTTP", "sse")
                    ],
                    value="stdio",
                    info="Communication protocol for the MCP service"
                )
        
        # Step 3: Function Selection (for function mode)
        with gr.Group(visible=False) as function_selection_group:
            gr.Markdown("### Step 3: Function Selection")
            create_help_text("Select which functions to expose as MCP tools.")
            
            available_functions = gr.CheckboxGroup(
                label="Available Functions",
                choices=[],
                interactive=True
            )
            
            function_details = gr.JSON(label="Function Details", visible=False)
        
        # Step 4: Parameter Configuration (for executable mode)
        with gr.Group(visible=False) as parameter_config_group:
            gr.Markdown("### Step 3: Parameter Configuration")
            create_help_text("Define parameters for the executable script.")
            
            parameters_json = gr.Code(
                label="Parameters Configuration (JSON)",
                language="json",
                value="{}",
                interactive=True,
                lines=10
            )
            
            validate_params_btn = create_action_button("✅ Validate Parameters", "secondary")
            param_validation_status = gr.Markdown("")
        
        # Step 5: Review and Create
        with gr.Group():
            gr.Markdown("### Final Step: Review and Create")
            
            with gr.Row():
                preview_config_btn = create_action_button("👁️ Preview Configuration", "secondary")
                create_service_btn = create_action_button("🚀 Create Service")
            
            config_preview = gr.JSON(label="Service Configuration Preview")
            creation_status = gr.Markdown("")
        
        # Event handlers
        def load_scripts() -> List[Tuple[str, str]]:
            """Load available scripts for dropdown."""
            try:
                api_client = get_api_client()
                result = api_client.list_scripts(limit=100)
                
                if "error" in result:
                    logger.error(f"Failed to load scripts: {result['error']}")
                    return []
                
                scripts = result.get("scripts", [])
                choices = []
                for script in scripts:
                    script_id = script.get("script_id", "")
                    filename = script.get("filename", "Unknown")
                    choices.append((f"{filename} ({script_id[:8]}...)", script_id))
                
                return choices
                
            except Exception as e:
                logger.error(f"Error loading scripts: {e}")
                return []
        
        def handle_script_selection(script_id: str) -> Tuple[Dict[str, Any], gr.Group, List[str], Dict[str, Any]]:
            """Handle script selection and load script details."""
            if not script_id:
                return {}, gr.Group(visible=False), [], {}
            
            try:
                api_client = get_api_client()
                
                # Get script details
                script_result = api_client.get_script(script_id)
                if "error" in script_result:
                    return {"error": script_result["error"]}, gr.Group(visible=False), [], {}
                
                # Get tool discovery results
                tools_result = api_client.discover_tools(script_id)
                if "error" in tools_result:
                    return script_result, gr.Group(visible=False), [], {}
                
                # Extract function information
                functions = tools_result.get("functions", [])
                function_choices = []
                function_details = {}
                
                for func in functions:
                    func_name = func.get("name", "")
                    func_doc = func.get("docstring", "No description")
                    function_choices.append(func_name)
                    function_details[func_name] = func
                
                return (
                    script_result,
                    gr.Group(visible=True),
                    function_choices,
                    function_details
                )
                
            except Exception as e:
                logger.error(f"Error handling script selection: {e}")
                return {"error": str(e)}, gr.Group(visible=False), [], {}
        
        def handle_hosting_mode_change(mode: str) -> Tuple[gr.Group, gr.Group]:
            """Handle hosting mode change to show/hide relevant sections."""
            if mode == "function":
                return gr.Group(visible=True), gr.Group(visible=False)
            else:
                return gr.Group(visible=False), gr.Group(visible=True)
        
        def validate_parameters(params_json: str) -> str:
            """Validate parameter configuration JSON."""
            is_valid, data, error = validate_json_input(params_json)
            
            if not is_valid:
                return f"❌ Invalid JSON: {error}"
            
            # Additional validation for parameter structure
            if not isinstance(data, dict):
                return "❌ Parameters must be a JSON object"
            
            return "✅ Parameters are valid"
        
        def preview_configuration(
            script_id: str, service_name: str, service_description: str,
            hosting_mode: str, protocol: str, selected_functions: List[str],
            parameters_json: str
        ) -> Dict[str, Any]:
            """Preview the service configuration."""
            config = {
                "script_id": script_id,
                "name": service_name,
                "description": service_description,
                "type": hosting_mode,
                "hosting_mode": protocol,
                "status": "active"
            }
            
            if hosting_mode == "function" and selected_functions:
                config["selected_functions"] = selected_functions
            elif hosting_mode == "executable":
                is_valid, params_data, error = validate_json_input(parameters_json)
                if is_valid:
                    config["parameters"] = params_data
                else:
                    config["parameters_error"] = error
            
            return config
        
        def create_service(
            script_id: str, service_name: str, service_description: str,
            hosting_mode: str, protocol: str, selected_functions: List[str],
            parameters_json: str
        ) -> str:
            """Create the MCP service."""
            if not all([script_id, service_name]):
                return "❌ Please fill in all required fields"
            
            try:
                # Build service configuration
                config = {
                    "script_id": script_id,
                    "name": service_name,
                    "description": service_description,
                    "type": hosting_mode,
                    "hosting_mode": protocol,
                    "status": "active"
                }
                
                if hosting_mode == "function":
                    if not selected_functions:
                        return "❌ Please select at least one function for function mode"
                    config["selected_functions"] = selected_functions
                elif hosting_mode == "executable":
                    is_valid, params_data, error = validate_json_input(parameters_json)
                    if not is_valid:
                        return f"❌ Invalid parameters JSON: {error}"
                    config["parameters"] = params_data
                
                # Create service via API
                api_client = get_api_client()
                result = api_client.create_service(config)
                
                if "error" in result:
                    return f"❌ Failed to create service: {result['error']}"
                
                service_id = result.get("service_id", "Unknown")
                return f"✅ Service created successfully!\n\n**Service ID**: {service_id}"
                
            except Exception as e:
                logger.error(f"Error creating service: {e}")
                return f"❌ Error: {str(e)}"
        
        # Wire up event handlers
        refresh_scripts_btn.click(
            fn=load_scripts,
            outputs=[script_dropdown]
        )
        
        script_dropdown.change(
            fn=handle_script_selection,
            inputs=[script_dropdown],
            outputs=[script_info, function_selection_group, available_functions, function_details]
        )
        
        hosting_mode.change(
            fn=handle_hosting_mode_change,
            inputs=[hosting_mode],
            outputs=[function_selection_group, parameter_config_group]
        )
        
        validate_params_btn.click(
            fn=validate_parameters,
            inputs=[parameters_json],
            outputs=[param_validation_status]
        )
        
        preview_config_btn.click(
            fn=preview_configuration,
            inputs=[
                script_dropdown, service_name, service_description,
                hosting_mode, protocol, available_functions, parameters_json
            ],
            outputs=[config_preview]
        )
        
        create_service_btn.click(
            fn=create_service,
            inputs=[
                script_dropdown, service_name, service_description,
                hosting_mode, protocol, available_functions, parameters_json
            ],
            outputs=[creation_status]
        )
        
        # Load initial data
        tab.load(
            fn=load_scripts,
            outputs=[script_dropdown]
        )
    
    return tab
