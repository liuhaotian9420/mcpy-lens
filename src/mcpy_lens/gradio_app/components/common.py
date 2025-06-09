"""Common Gradio components and utilities."""

import gradio as gr
from typing import Any, Dict, List, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)


def create_error_display(message: str) -> gr.Markdown:
    """Create an error display component.
    
    Args:
        message: Error message to display
        
    Returns:
        Gradio Markdown component with error styling
    """
    return gr.Markdown(
        f"❌ **Error**: {message}",
        elem_classes=["error-message"]
    )


def create_success_display(message: str) -> gr.Markdown:
    """Create a success display component.
    
    Args:
        message: Success message to display
        
    Returns:
        Gradio Markdown component with success styling
    """
    return gr.Markdown(
        f"✅ **Success**: {message}",
        elem_classes=["success-message"]
    )


def create_info_display(message: str) -> gr.Markdown:
    """Create an info display component.
    
    Args:
        message: Info message to display
        
    Returns:
        Gradio Markdown component with info styling
    """
    return gr.Markdown(
        f"ℹ️ **Info**: {message}",
        elem_classes=["info-message"]
    )


def format_json_display(data: Dict[str, Any]) -> str:
    """Format data for JSON display.
    
    Args:
        data: Data to format
        
    Returns:
        Formatted JSON string
    """
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to format JSON: {e}")
        return str(data)


def create_status_badge(status: str) -> str:
    """Create a status badge for display.
    
    Args:
        status: Status string
        
    Returns:
        Formatted status badge
    """
    status_colors = {
        "active": "🟢",
        "inactive": "🔴", 
        "error": "🔴",
        "pending": "🟡",
        "healthy": "🟢",
        "unhealthy": "🔴",
        "unknown": "⚪"
    }
    
    color = status_colors.get(status.lower(), "⚪")
    return f"{color} {status.title()}"


def safe_get_nested(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """Safely get nested dictionary values.
    
    Args:
        data: Dictionary to search
        keys: List of keys to traverse
        default: Default value if key not found
        
    Returns:
        Value at nested key or default
    """
    try:
        result = data
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError):
        return default


def create_loading_message() -> str:
    """Create a loading message."""
    return "⏳ Loading..."


def create_empty_state_message(entity: str) -> str:
    """Create an empty state message.
    
    Args:
        entity: Name of the entity (e.g., "scripts", "services")
        
    Returns:
        Empty state message
    """
    return f"No {entity} found. Upload or create some to get started!"


def validate_json_input(json_str: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Validate JSON input string.
    
    Args:
        json_str: JSON string to validate
        
    Returns:
        Tuple of (is_valid, parsed_data, error_message)
    """
    if not json_str.strip():
        return False, None, "JSON input is empty"
    
    try:
        data = json.loads(json_str)
        return True, data, None
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON: {str(e)}"


def create_refresh_button(label: str = "🔄 Refresh") -> gr.Button:
    """Create a refresh button with consistent styling.
    
    Args:
        label: Button label
        
    Returns:
        Gradio Button component
    """
    return gr.Button(
        label,
        variant="secondary",
        size="sm",
        elem_classes=["refresh-button"]
    )


def create_action_button(label: str, variant: str = "primary") -> gr.Button:
    """Create an action button with consistent styling.
    
    Args:
        label: Button label
        variant: Button variant (primary, secondary, stop)
        
    Returns:
        Gradio Button component
    """
    return gr.Button(
        label,
        variant=variant,
        elem_classes=["action-button"]
    )


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display.
    
    Args:
        timestamp: ISO timestamp string
        
    Returns:
        Formatted timestamp
    """
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp


def create_help_text(text: str) -> gr.Markdown:
    """Create help text component.
    
    Args:
        text: Help text content
        
    Returns:
        Gradio Markdown component with help styling
    """
    return gr.Markdown(
        text,
        elem_classes=["help-text"]
    )
