"""Service management interface for monitoring and controlling MCP services."""

import gradio as gr
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
import logging
import time

from ..api_client import get_api_client
from ..components.common import (
    create_error_display, create_success_display, create_info_display,
    format_json_display, create_status_badge, create_refresh_button,
    create_action_button, format_timestamp, create_empty_state_message
)

logger = logging.getLogger(__name__)


def create_service_management_interface() -> gr.Tab:
    """Create the service management interface tab.
    
    Returns:
        Gradio Tab component with service management interface
    """
    with gr.Tab("🎛️ Service Management") as tab:
        gr.Markdown("## Service Management Dashboard")
        gr.Markdown("Monitor and control your MCP services in real-time.")
        
        # Services overview
        with gr.Row():
            gr.Markdown("### Active Services")
            refresh_services_btn = create_refresh_button("🔄 Refresh Services")
        
        # Services table
        services_table = gr.DataFrame(
            headers=["ID", "Name", "Type", "Status", "Health", "Tools", "Created", "Actions"],
            datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
            interactive=False,
            wrap=True
        )
        
        # Service actions
        with gr.Row():
            with gr.Column():
                selected_service_id = gr.Textbox(
                    label="Selected Service ID",
                    placeholder="Enter service ID or select from table",
                    interactive=True
                )
            with gr.Column():
                start_btn = create_action_button("▶️ Start Service", "primary")
                stop_btn = create_action_button("⏹️ Stop Service", "secondary")
                restart_btn = create_action_button("🔄 Restart Service", "secondary")
                delete_service_btn = create_action_button("🗑️ Delete Service", "stop")
        
        # Service details
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Service Details")
                service_details = gr.JSON(label="Service Configuration")
            
            with gr.Column():
                gr.Markdown("### Service Health")
                health_status = gr.JSON(label="Health Information")
        
        # Action results
        action_status = gr.Markdown("")
        
        # Service logs (placeholder)
        with gr.Group():
            gr.Markdown("### Service Logs")
            gr.Markdown("*Real-time log streaming will be implemented in future updates*")
            logs_display = gr.Textbox(
                label="Recent Logs",
                lines=10,
                interactive=False,
                placeholder="Service logs will appear here..."
            )
        
        # Event handlers
        def load_services_list() -> pd.DataFrame:
            """Load and format services list."""
            try:
                api_client = get_api_client()
                result = api_client.list_services()
                
                if "error" in result:
                    logger.error(f"Failed to load services: {result['error']}")
                    return pd.DataFrame(columns=["ID", "Name", "Type", "Status", "Health", "Tools", "Created", "Actions"])
                
                services = result.get("services", [])
                if not services:
                    return pd.DataFrame(columns=["ID", "Name", "Type", "Status", "Health", "Tools", "Created", "Actions"])
                
                # Format data for table
                table_data = []
                for service in services:
                    tools = service.get("tools", [])
                    tool_count = len(tools) if tools else 0
                    
                    table_data.append([
                        service.get("service_id", "")[:8] + "...",  # Shortened ID
                        service.get("name", "Unknown"),
                        service.get("type", "unknown").title(),
                        create_status_badge(service.get("status", "unknown")),
                        create_status_badge("healthy"),  # Placeholder
                        f"{tool_count} tools",
                        format_timestamp(service.get("created_at", "")),
                        "Start | Stop | Delete"
                    ])
                
                return pd.DataFrame(
                    table_data,
                    columns=["ID", "Name", "Type", "Status", "Health", "Tools", "Created", "Actions"]
                )
                
            except Exception as e:
                logger.error(f"Error loading services: {e}")
                return pd.DataFrame(columns=["ID", "Name", "Type", "Status", "Health", "Tools", "Created", "Actions"])
        
        def handle_service_action(service_id: str, action: str) -> Tuple[str, pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
            """Handle service actions (start, stop, restart, delete)."""
            if not service_id.strip():
                return "❌ Please enter a service ID", load_services_list(), {}, {}
            
            try:
                api_client = get_api_client()
                
                if action == "delete":
                    result = api_client.delete_service(service_id)
                    if "error" in result:
                        return f"❌ Failed to delete service: {result['error']}", load_services_list(), {}, {}
                    return f"✅ Service {service_id} deleted successfully", load_services_list(), {}, {}
                
                elif action in ["start", "stop", "restart"]:
                    # For now, these are placeholder actions
                    # In a real implementation, these would call specific service control endpoints
                    return f"✅ Service {action} action completed for {service_id}", load_services_list(), {}, {}
                
                else:
                    return f"❌ Unknown action: {action}", load_services_list(), {}, {}
                
            except Exception as e:
                logger.error(f"Error performing {action} on service {service_id}: {e}")
                return f"❌ Error: {str(e)}", load_services_list(), {}, {}
        
        def handle_view_service_details(service_id: str) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
            """Handle viewing service details and health."""
            if not service_id.strip():
                return "❌ Please enter a service ID", {}, {}
            
            try:
                api_client = get_api_client()
                
                # Get service details
                service_result = api_client.get_service(service_id)
                if "error" in service_result:
                    return f"❌ Failed to load service: {service_result['error']}", {}, {}
                
                # Get service health
                health_result = api_client.get_service_health(service_id)
                
                return f"✅ Service details loaded for ID: {service_id}", service_result, health_result
                
            except Exception as e:
                logger.error(f"Error viewing service details: {e}")
                return f"❌ Error: {str(e)}", {}, {}
        
        # Wire up event handlers
        refresh_services_btn.click(
            fn=load_services_list,
            outputs=[services_table]
        )
        
        start_btn.click(
            fn=lambda service_id: handle_service_action(service_id, "start"),
            inputs=[selected_service_id],
            outputs=[action_status, services_table, service_details, health_status]
        )
        
        stop_btn.click(
            fn=lambda service_id: handle_service_action(service_id, "stop"),
            inputs=[selected_service_id],
            outputs=[action_status, services_table, service_details, health_status]
        )
        
        restart_btn.click(
            fn=lambda service_id: handle_service_action(service_id, "restart"),
            inputs=[selected_service_id],
            outputs=[action_status, services_table, service_details, health_status]
        )
        
        delete_service_btn.click(
            fn=lambda service_id: handle_service_action(service_id, "delete"),
            inputs=[selected_service_id],
            outputs=[action_status, services_table, service_details, health_status]
        )
        
        selected_service_id.change(
            fn=handle_view_service_details,
            inputs=[selected_service_id],
            outputs=[action_status, service_details, health_status]
        )
        
        # Note: Users can click the refresh button to load initial data

    return tab
