"""
Script wrapper generator for mcpy-lens.

This module provides functionality for generating Typer CLI wrappers
for Python scripts to enable them to be used as MCP tools.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any, Optional, List, Dict

from .script_validation import validate_script_entry_point, extract_script_params


def generate_file_typer_wrapper(
    script_path: Path,
    script_id: str,
    output_dir: Path,
    script_args: Optional[list[Dict[str, Any]]] = None,
) -> Path:
    """
    Generate a Typer CLI wrapper for an entire Python script.
    
    Args:
        script_path: Path to the original Python script
        script_id: Unique identifier for the script
        output_dir: Directory to save the wrapper
        script_args: List of script-level arguments to expose in the CLI
        
    Returns:
        Path to the generated wrapper script
    """
    if not script_id:
        script_id = f"{script_path.stem}_{uuid.uuid4().hex[:8]}"
        
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    
    wrapper_file = output_dir / f"{script_id}_wrapper.py"
    
    # If script_args not provided, try to extract them from the script
    if script_args is None:
        script_args = extract_script_params(script_path)
    
    # Create wrapper content
    wrapper_content = [
        "#!/usr/bin/env python",
        f"\"\"\"Typer CLI wrapper for {script_path.name}\"\"\"",
        "",
        "import sys",
        "import json",
        "import subprocess",
        "from pathlib import Path",
        "import typer",
        "",
        "app = typer.Typer()",
        "",
        "@app.command()",
        "def main(",
    ]
    
    # Add script parameters to CLI definition
    for arg in script_args:
        arg_name = arg["name"]
        arg_type = arg.get("type", "string")
        arg_flag = arg.get("flag", f"--{arg_name}")
        arg_help = arg.get("help", f"Parameter {arg_name}")
        arg_required = arg.get("required", False)
        arg_default = arg.get("default")
        
        # Map Python types to Typer types
        if arg_type == "string":
            py_type = "str"
        elif arg_type == "integer":
            py_type = "int"
        elif arg_type == "number":
            py_type = "float"
        elif arg_type == "boolean":
            py_type = "bool"
        else:
            py_type = "str"  # Default
            
        # Create parameter definition
        param_def = f"    {arg_name}: {py_type}"
        
        # Add typer.Option annotation
        if arg_required:
            param_def += f" = typer.Option(..., \"{arg_flag}\", help=\"{arg_help}\")"
        else:
            default_value = "None" if arg_default is None else arg_default
            if arg_type == "string" and arg_default is not None:
                default_value = f"\"{arg_default}\""
            param_def += f" = typer.Option({default_value}, \"{arg_flag}\", help=\"{arg_help}\")"
            
        param_def += ","
        wrapper_content.append(param_def)
    
    # Close parameter list and add function body
    wrapper_content.extend([
        "):",
        "    \"\"\"Run the wrapped script with provided arguments\"\"\"",
        f"    script_path = Path(r\"{script_path}\")",
        "    cmd = [sys.executable, str(script_path)]",
    ])
    
    # Add argument mapping
    for arg in script_args:
        arg_name = arg["name"]
        arg_flag = arg.get("flag", f"--{arg_name}")
        arg_type = arg.get("type", "string")
        
        if arg_type == "boolean":
            wrapper_content.append(f"    if {arg_name}:")
            wrapper_content.append(f"        cmd.append(\"{arg_flag}\")")
        else:
            wrapper_content.append(f"    if {arg_name} is not None:")
            wrapper_content.append(f"        cmd.extend([\"{arg_flag}\", str({arg_name})])")
    
    # Add execution code
    wrapper_content.extend([
        "",
        "    try:",
        "        # Execute the script with provided arguments",
        "        process = subprocess.run(cmd, capture_output=True, text=True, check=False)",
        "        ",
        "        # Check for errors",
        "        if process.returncode != 0:",
        "            print(json.dumps({\"error\": process.stderr.strip()}), file=sys.stderr)",
        "            sys.exit(process.returncode)",
        "        ",
        "        # Output the result as JSON",
        "        print(json.dumps({\"result\": process.stdout.strip()}, default=str))",
        "    except Exception as e:",
        "        print(json.dumps({\"error\": str(e)}), file=sys.stderr)",
        "        sys.exit(1)",
        "",
        "",
        "if __name__ == \"__main__\":",
        "    app()",
    ])
    
    # Write wrapper file
    with open(wrapper_file, "w", encoding="utf-8") as f:
        f.write("\n".join(wrapper_content))
        
    # Make executable on Unix-like systems
    if os.name != "nt":
        wrapper_file.chmod(wrapper_file.stat().st_mode | 0o755)
    
    return wrapper_file


def create_tool_metadata_file(
    script_path: Path,
    script_id: str,
    wrapper_path: Path,
    script_args: list[Dict[str, Any]],
    output_dir: Path,
    description: str = ""
) -> Path:
    """
    Create a metadata file for MCP tool registration.
    
    Args:
        script_path: Path to the original Python script
        script_id: Unique identifier for the script
        wrapper_path: Path to the generated wrapper script
        script_args: List of script arguments as dictionaries
        output_dir: Directory to save the metadata
        description: Optional description for the tool
        
    Returns:
        Path to the generated metadata file
    """
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        
    metadata_file = output_dir / f"{script_id}.json"
    
    # Extract script name for tool name
    tool_name = script_path.stem
    
    # Create input schema from script args
    input_properties = {}
    required = []
    
    for arg in script_args:
        arg_name = arg["name"]
        prop = {
            "type": arg.get("type", "string"),
            "description": arg.get("help", f"Parameter {arg_name}")
        }
        
        if "default" in arg:
            prop["default"] = arg["default"]
            
        if arg.get("required", False):
            required.append(arg_name)
            
        input_properties[arg_name] = prop
    
    # Create tool metadata
    metadata = {
        "tool_id": script_id,
        "name": tool_name,
        "description": description or f"Wrapper for {script_path.name}",
        "version": "1.0.0",
        "input_schema": {
            "type": "object",
            "properties": input_properties,
            "required": required
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "Script output"}
            }
        },
        "executable": {
            "path": str(wrapper_path),
            "type": "python",
            "arguments": []
        },
        "source_file": str(script_path),
        "created_at": str(Path(script_path).stat().st_mtime),
    }
    
    # Write metadata file
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    return metadata_file
