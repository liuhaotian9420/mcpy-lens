"""Service testing interface for interactive tool testing."""

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


def create_service_testing_interface() -> gr.Tab:
    """Create the service testing interface tab.
    
    Returns:
        Gradio Tab component with service testing interface
    """
    with gr.Tab("🧪 Service Testing") as tab:
        gr.Markdown("## Service Testing Interface")
        gr.Markdown("Test your MCP services interactively with dynamic parameter forms.")
        
        # Service and tool selection
        with gr.Group():
            gr.Markdown("### Select Service and Tool")
            with gr.Row():
                # Load services automatically on initialization
                def load_initial_services():
                    """Load services on page initialization."""
                    try:
                        api_client = get_api_client()
                        result = api_client.list_services()

                        if "error" in result:
                            logger.error(f"Failed to load initial services: {result['error']}")
                            return []

                        services = result.get("services", [])
                        choices = []
                        for service in services:
                            service_id = service.get("service_id", "")
                            name = service.get("name", "Unknown")
                            choices.append((f"{name} ({service_id[:8]}...)", service_id))

                        logger.info(f"Loaded {len(choices)} services on initialization")
                        return choices
                    except Exception as e:
                        logger.error(f"Error loading initial services: {e}")
                        return []

                initial_service_choices = load_initial_services()

                service_dropdown = gr.Dropdown(
                    label="Select Service",
                    choices=initial_service_choices,
                    interactive=True,
                    allow_custom_value=False
                )
                refresh_services_btn = create_refresh_button("🔄 Refresh Services")
            
            tool_dropdown = gr.Dropdown(
                label="Select Tool",
                choices=[],
                interactive=True,
                allow_custom_value=False,
                visible=False
            )
            
            tool_info = gr.JSON(label="Tool Information", visible=False)
        
        # Parameter input section
        with gr.Group(visible=False) as parameter_section:
            gr.Markdown("### Tool Parameters")
            create_help_text("Fill in the parameters for the selected tool.")
            
            # Dynamic parameter inputs will be created here
            parameters_json = gr.Code(
                label="Parameters (JSON)",
                language="json",
                value="{}",
                interactive=True,
                lines=8
            )
            
            validate_params_btn = create_action_button("✅ Validate Parameters", "secondary")
            param_validation_status = gr.Markdown("")
        
        # Test execution section
        with gr.Group(visible=False) as execution_section:
            gr.Markdown("### Execute Test")
            
            with gr.Row():
                execute_btn = create_action_button("🚀 Execute Tool", "primary")
                clear_btn = create_action_button("🧹 Clear Results", "secondary")
            
            execution_status = gr.Markdown("")
        
        # Results section
        with gr.Group():
            gr.Markdown("### Test Results")
            
            with gr.Tabs():
                with gr.Tab("Response"):
                    response_display = gr.JSON(label="Tool Response")
                
                with gr.Tab("Raw Output"):
                    raw_output = gr.Textbox(
                        label="Raw Response",
                        lines=10,
                        interactive=False
                    )
                
                with gr.Tab("Streaming Output"):
                    streaming_output = gr.Textbox(
                        label="Streaming Response",
                        lines=10,
                        interactive=False,
                        placeholder="Streaming output will appear here for tools that support it..."
                    )
        
        # Request history section
        with gr.Group():
            gr.Markdown("### Request History")
            create_help_text("Previous test requests for easy reuse.")
            
            history_dropdown = gr.Dropdown(
                label="Previous Requests",
                choices=[],
                interactive=True,
                allow_custom_value=False
            )
            
            load_history_btn = create_action_button("📋 Load Request", "secondary")
            save_request_btn = create_action_button("💾 Save Request", "secondary")
        
        # Event handlers

        
        def handle_service_selection(service_id: str) -> Tuple[gr.Dropdown, List[str], Dict[str, Any]]:
            """Handle service selection and load available tools."""
            if not service_id:
                return gr.Dropdown(visible=False), [], {}
            
            try:
                api_client = get_api_client()
                
                # Get service details
                service_result = api_client.get_service(service_id)
                if "error" in service_result:
                    return gr.Dropdown(visible=False), [], {"error": service_result["error"]}
                
                # Extract tools from service
                tools = service_result.get("tools", [])
                tool_choices = []
                
                for tool in tools:
                    tool_name = tool.get("name", "")
                    tool_description = tool.get("description", "No description")
                    tool_choices.append(f"{tool_name} - {tool_description}")
                
                if tool_choices:
                    return gr.Dropdown(visible=True, choices=tool_choices), tool_choices, service_result
                else:
                    return gr.Dropdown(visible=False), [], {"message": "No tools found in this service"}
                
            except Exception as e:
                logger.error(f"Error handling service selection: {e}")
                return gr.Dropdown(visible=False), [], {"error": str(e)}
        
        def handle_tool_selection(tool_name: str, service_data: Dict[str, Any]) -> Tuple[gr.Group, gr.Group, Dict[str, Any], str]:
            """Handle tool selection and show parameter form."""
            if not tool_name or not service_data:
                return gr.Group(visible=False), gr.Group(visible=False), {}, "{}"
            
            try:
                # Extract tool name from the dropdown selection
                actual_tool_name = tool_name.split(" - ")[0] if " - " in tool_name else tool_name
                
                # Find the tool in service data
                tools = service_data.get("tools", [])
                selected_tool = None
                
                for tool in tools:
                    if tool.get("name") == actual_tool_name:
                        selected_tool = tool
                        break
                
                if not selected_tool:
                    return gr.Group(visible=False), gr.Group(visible=False), {"error": "Tool not found"}, "{}"
                
                # Generate parameter template
                parameters = selected_tool.get("parameters", {})
                properties = parameters.get("properties", {})
                required = parameters.get("required", [])
                
                param_template = {}
                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "string")
                    param_default = param_info.get("default")
                    
                    if param_default is not None:
                        param_template[param_name] = param_default
                    elif param_type == "string":
                        param_template[param_name] = ""
                    elif param_type == "number":
                        param_template[param_name] = 0
                    elif param_type == "boolean":
                        param_template[param_name] = False
                    elif param_type == "array":
                        param_template[param_name] = []
                    elif param_type == "object":
                        param_template[param_name] = {}
                
                param_json = json.dumps(param_template, indent=2)
                
                return (
                    gr.Group(visible=True),
                    gr.Group(visible=True),
                    selected_tool,
                    param_json
                )
                
            except Exception as e:
                logger.error(f"Error handling tool selection: {e}")
                return gr.Group(visible=False), gr.Group(visible=False), {"error": str(e)}, "{}"
        
        def validate_parameters(params_json: str) -> str:
            """Validate parameter JSON."""
            is_valid, data, error = validate_json_input(params_json)
            
            if not is_valid:
                return f"❌ Invalid JSON: {error}"
            
            return "✅ Parameters are valid JSON"
        
        def execute_tool_test(service_id: str, tool_name: str, params_json: str) -> Tuple[str, Dict[str, Any], str]:
            """Execute the tool test."""
            if not all([service_id, tool_name, params_json]):
                return "❌ Please select a service, tool, and provide parameters", {}, ""
            
            try:
                # Validate parameters
                is_valid, params_data, error = validate_json_input(params_json)
                if not is_valid:
                    return f"❌ Invalid parameters: {error}", {}, ""
                
                # For now, this is a mock implementation
                # In a real implementation, this would call the actual tool via the MCP protocol
                mock_response = {
                    "status": "success",
                    "result": f"Mock response for tool '{tool_name}' with parameters: {params_data}",
                    "execution_time": "0.123s",
                    "timestamp": "2025-06-03T12:00:00Z"
                }
                
                raw_output = json.dumps(mock_response, indent=2)
                
                return "✅ Tool executed successfully", mock_response, raw_output
                
            except Exception as e:
                logger.error(f"Error executing tool test: {e}")
                return f"❌ Error: {str(e)}", {}, ""
        
        def clear_results() -> Tuple[str, Dict[str, Any], str, str]:
            """Clear all test results."""
            return "", {}, "", ""
        
        # Wire up event handlers
        def update_service_dropdown():
            """Update service dropdown with fresh data."""
            try:
                api_client = get_api_client()
                result = api_client.list_services()

                if "error" in result:
                    logger.error(f"Failed to load services: {result['error']}")
                    return gr.Dropdown(
                        label="Select Service",
                        choices=[],
                        value=None,
                        interactive=True,
                        allow_custom_value=False
                    )

                services = result.get("services", [])
                choices = []
                for service in services:
                    service_id = service.get("service_id", "")
                    name = service.get("name", "Unknown")
                    choices.append((f"{name} ({service_id[:8]}...)", service_id))

                logger.info(f"Loaded {len(choices)} services for dropdown")
                return gr.Dropdown(
                    label="Select Service",
                    choices=choices,
                    value=None,
                    interactive=True,
                    allow_custom_value=False
                )

            except Exception as e:
                logger.error(f"Error loading services: {e}")
                return gr.Dropdown(
                    label="Select Service",
                    choices=[],
                    value=None,
                    interactive=True,
                    allow_custom_value=False
                )

        refresh_services_btn.click(
            fn=update_service_dropdown,
            outputs=[service_dropdown]
        )
        
        service_dropdown.change(
            fn=handle_service_selection,
            inputs=[service_dropdown],
            outputs=[tool_dropdown, tool_dropdown, tool_info]
        )
        
        tool_dropdown.change(
            fn=handle_tool_selection,
            inputs=[tool_dropdown, tool_info],
            outputs=[parameter_section, execution_section, tool_info, parameters_json]
        )
        
        validate_params_btn.click(
            fn=validate_parameters,
            inputs=[parameters_json],
            outputs=[param_validation_status]
        )
        
        execute_btn.click(
            fn=execute_tool_test,
            inputs=[service_dropdown, tool_dropdown, parameters_json],
            outputs=[execution_status, response_display, raw_output]
        )
        
        clear_btn.click(
            fn=clear_results,
            outputs=[execution_status, response_display, raw_output, streaming_output]
        )
        
        # Note: Users can click the refresh button to load initial data

    return tab
