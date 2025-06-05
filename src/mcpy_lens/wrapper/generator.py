"""
Wrapper generator that creates MCP-compatible wrappers from tool metadata.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import tempfile
import shutil

from ..models import ScriptMetadata, ToolInfo
from .config import WrapperConfig

logger = logging.getLogger(__name__)


class WrapperGenerator:
    """Generates MCP-compatible wrappers from script metadata."""
    
    def __init__(self, config: WrapperConfig = None):
        self.config = config or WrapperConfig.from_env()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def generate_wrapper(
        self,
        script_path: Path,
        script_metadata: ScriptMetadata,
        selected_functions: List[str],
        output_dir: Path
    ) -> Dict[str, Path]:
        """
        Generate a complete MCP wrapper for a script.
        
        Args:
            script_path: Path to the original Python script
            script_metadata: Metadata about the script
            selected_functions: List of function names to expose as tools
            output_dir: Directory to save the generated wrapper
            
        Returns:
            Dictionary with paths to generated files
        """
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate tool metadata
            tool_metadata = self._create_tool_metadata(script_metadata, selected_functions)
            
            # Save metadata file
            metadata_path = output_dir / f"{script_metadata.script_id}_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(tool_metadata, f, indent=2, default=str)
            
            # Copy the original script
            script_copy_path = output_dir / f"{script_metadata.script_id}.py"
            shutil.copy2(script_path, script_copy_path)
            
            # Generate the wrapper executable
            wrapper_path = self._generate_wrapper_executable(
                script_metadata.script_id,
                script_copy_path,
                metadata_path,
                output_dir
            )
            
            # Generate configuration file
            config_path = self._generate_config_file(output_dir)
            
            # Generate README
            readme_path = self._generate_readme(
                script_metadata, selected_functions, output_dir
            )
            
            self.logger.info(f"Generated wrapper for script {script_metadata.script_id}")
            
            return {
                "wrapper": wrapper_path,
                "metadata": metadata_path,
                "script": script_copy_path,
                "config": config_path,
                "readme": readme_path
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate wrapper: {e}")
            raise
    
    def _create_tool_metadata(
        self, 
        script_metadata: ScriptMetadata, 
        selected_functions: List[str]
    ) -> Dict[str, Any]:
        """Create tool metadata for the selected functions."""
        tools = []
        
        for func in script_metadata.functions:
            if func.name in selected_functions:
                # Convert function info to tool format
                tool = {
                    "name": func.name,
                    "description": func.description or f"Execute {func.name} function",
                    "input_schema": self._create_input_schema(func),
                    "output_schema": self._create_output_schema(func)
                }
                tools.append(tool)
        
        return {
            "script_info": {
                "script_id": script_metadata.script_id,
                "filename": script_metadata.filename,
                "upload_time": script_metadata.upload_time.isoformat(),
                "file_size": script_metadata.file_size
            },
            "tools": tools,
            "metadata_version": "1.0",
            "generated_by": "mcpy-lens"
        }
    
    def _create_input_schema(self, func_info) -> Dict[str, Any]:
        """Create JSON schema for function input parameters."""
        properties = {}
        required = []
        
        for param_name, param_type in func_info.parameters.items():
            # Convert Python types to JSON schema types
            json_type = self._python_type_to_json_type(param_type)
            properties[param_name] = {
                "type": json_type,
                "description": f"Parameter {param_name} of type {param_type}"
            }
            required.append(param_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _create_output_schema(self, func_info) -> Dict[str, Any]:
        """Create JSON schema for function output."""
        return_type = self._python_type_to_json_type(func_info.return_type)
        
        return {
            "type": "object",
            "properties": {
                "result": {
                    "type": return_type,
                    "description": f"Function result of type {func_info.return_type}"
                },
                "success": {
                    "type": "boolean",
                    "description": "Whether the function executed successfully"
                }
            }
        }
    
    def _python_type_to_json_type(self, python_type: str) -> str:
        """Convert Python type annotation to JSON schema type."""
        type_mapping = {
            "str": "string",
            "int": "integer", 
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "Any": "string"  # Default fallback
        }
        
        # Handle complex types (just use the base type for now)
        base_type = python_type.split("[")[0].split("(")[0].strip()
        return type_mapping.get(base_type, "string")
    
    def _generate_wrapper_executable(
        self,
        script_id: str,
        script_path: Path,
        metadata_path: Path,
        output_dir: Path
    ) -> Path:
        """Generate the main wrapper executable."""
        wrapper_content = f'''#!/usr/bin/env python3
"""
MCP Wrapper for script: {script_id}
Generated by mcpy-lens

This wrapper provides MCP-compatible access to the functions in the original script.
"""

import sys
import asyncio
from pathlib import Path

# Add the wrapper module to path
wrapper_dir = Path(__file__).parent
sys.path.insert(0, str(wrapper_dir))

try:
    from mcpy_lens.wrapper import ScriptWrapper, WrapperConfig
except ImportError:
    print("Error: mcpy-lens wrapper module not found. Please ensure mcpy-lens is installed.")
    sys.exit(1)


def main():
    """Main entry point for the wrapper."""
    script_path = Path(__file__).parent / "{script_path.name}"
    metadata_path = Path(__file__).parent / "{metadata_path.name}"
    
    if not script_path.exists():
        print(f"Error: Script file not found: {{script_path}}")
        sys.exit(1)
    
    if not metadata_path.exists():
        print(f"Error: Metadata file not found: {{metadata_path}}")
        sys.exit(1)
    
    # Load configuration
    config = WrapperConfig.from_env()
    
    # Create and run wrapper
    wrapper = ScriptWrapper(
        script_path=script_path,
        metadata_path=metadata_path,
        config=config
    )
    
    try:
        asyncio.run(wrapper.run())
    except KeyboardInterrupt:
        print("Wrapper interrupted by user", file=sys.stderr)
    except Exception as e:
        print(f"Wrapper error: {{e}}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
        
        wrapper_path = output_dir / f"{script_id}_wrapper.py"
        with open(wrapper_path, 'w', encoding='utf-8') as f:
            f.write(wrapper_content)
        
        # Make executable on Unix systems
        try:
            wrapper_path.chmod(0o755)
        except Exception:
            pass  # Windows doesn't support chmod
        
        return wrapper_path
    
    def _generate_config_file(self, output_dir: Path) -> Path:
        """Generate a configuration file for the wrapper."""
        config_content = """# MCP Wrapper Configuration
# Environment variables for wrapper execution

# Resource limits
WRAPPER_MAX_EXECUTION_TIME=300
WRAPPER_MAX_MEMORY_MB=512
WRAPPER_MAX_OUTPUT_LINES=10000
WRAPPER_MAX_CONCURRENT=8

# Execution settings
WRAPPER_PYTHON_EXECUTABLE=python
# WRAPPER_WORKING_DIR=/path/to/working/directory

# Streaming settings
WRAPPER_STREAM_BUFFER=1024
WRAPPER_STREAM_FLUSH=0.1

# Security settings
WRAPPER_ALLOW_NETWORK=true
WRAPPER_ALLOW_FILE_WRITE=true
"""
        
        config_path = output_dir / "wrapper.env"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        return config_path
    
    def _generate_readme(
        self,
        script_metadata: ScriptMetadata,
        selected_functions: List[str],
        output_dir: Path
    ) -> Path:
        """Generate a README file for the wrapper."""
        readme_content = f"""# MCP Wrapper for {script_metadata.filename}

This directory contains an MCP-compatible wrapper for the Python script `{script_metadata.filename}`.

## Files

- `{script_metadata.script_id}_wrapper.py` - Main wrapper executable
- `{script_metadata.script_id}.py` - Original Python script
- `{script_metadata.script_id}_metadata.json` - Tool metadata
- `wrapper.env` - Configuration file
- `README.md` - This file

## Available Tools

The following functions are exposed as MCP tools:

{chr(10).join(f"- {func}" for func in selected_functions)}

## Usage

### As MCP Server

Run the wrapper as an MCP server:

```bash
python {script_metadata.script_id}_wrapper.py
```

The wrapper will read JSON-RPC requests from stdin and write responses to stdout.

### Configuration

Set environment variables or edit `wrapper.env` to configure the wrapper:

- `WRAPPER_MAX_EXECUTION_TIME` - Maximum execution time in seconds (default: 300)
- `WRAPPER_MAX_MEMORY_MB` - Maximum memory usage in MB (default: 512)
- `WRAPPER_PYTHON_EXECUTABLE` - Python executable to use (default: python)

### Testing

You can test the wrapper using the MCP Inspector or any MCP-compatible client.

## Requirements

- Python >= 3.10
- mcpy-lens package
- Dependencies required by the original script

## Generated Information

- Script ID: {script_metadata.script_id}
- Original filename: {script_metadata.filename}
- Upload time: {script_metadata.upload_time}
- File size: {script_metadata.file_size} bytes
- Functions: {len(script_metadata.functions)} total, {len(selected_functions)} exposed
"""
        
        readme_path = output_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        return readme_path
