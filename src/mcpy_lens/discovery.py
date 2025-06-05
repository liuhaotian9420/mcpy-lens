"""
Tool discovery module for mcpy-lens.

This module provides functionality to discover Python functions from uploaded scripts
and generate JSON schemas for tool registration.
"""

import importlib.util
import inspect
import json
import logging
import os
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_type_hints

logger = logging.getLogger(__name__)


class ValidFileTypes(Enum):
    """Valid file types for tool discovery."""
    PYTHON = ".py"


def discover_py_files(source_path_str: str) -> list[Path]:
    """
    Discover Python files from a given file or directory path.

    Args:
        source_path_str: The path to a Python file or a directory.

    Returns:
        A list of Path objects for discovered .py files.

    Raises:
        FileNotFoundError: If the source_path does not exist.
        ValueError: If source_path is not a file or directory.
    """
    # Convert to absolute path
    source_path = Path(source_path_str).resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path_str}")

    py_files: list[Path] = []

    if source_path.is_file():
        if source_path.suffix == ValidFileTypes.PYTHON.value:
            py_files.append(source_path)
            logger.info(f"Discovered Python file: {source_path}")
        else:
            logger.warning(f"Source file is not a Python file, skipping: {source_path}")
    elif source_path.is_dir():
        logger.info(f"Scanning directory for Python files: {source_path}")
        for root, _, files in os.walk(source_path):
            root_path = Path(root)
            for file_name in files:
                if file_name.endswith(ValidFileTypes.PYTHON.value):
                    file_path = root_path / file_name
                    py_files.append(file_path)
                    rel_path = file_path.relative_to(source_path)
                    logger.debug(f"Discovered Python file: {rel_path} (full path: {file_path})")
    else:
        raise ValueError(f"Source path is not a file or directory: {source_path}")

    if not py_files:
        logger.warning(f"No Python files found in: {source_path}")
    else:
        logger.info(f"Discovered {len(py_files)} Python file(s) from {source_path}")

    return py_files


def _load_module_from_path(file_path: Path) -> Any | None:
    """
    Load a Python module dynamically from a file path.

    Args:
        file_path: The path to the Python file.

    Returns:
        The loaded module object, or None if loading fails.
    """
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))

    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"Failed to load module '{module_name}' from '{file_path}': {e}", exc_info=True)
            return None
    else:
        logger.error(f"Could not create module spec for '{file_path}'")
        return None


def discover_functions(
    file_paths: list[Path],
    target_function_names: list[str] | None = None
) -> list[tuple[Callable[..., Any], str, Path]]:
    """
    Discover functions from a list of Python files.

    Args:
        file_paths: A list of paths to Python files.
        target_function_names: Optional list of specific function names to discover.

    Returns:
        A list of tuples: (function_object, function_name, file_path)
    """
    discovered_functions: list[tuple[Callable[..., Any], str, Path]] = []
    function_name_set = set(target_function_names) if target_function_names else set()

    for file_path in file_paths:
        logger.info(f"Discovering functions in: {file_path}")
        module = _load_module_from_path(file_path)

        if module:
            logger.debug(f"Module loaded successfully: {module.__name__}")
            module_functions = []

            for name, member in inspect.getmembers(module):
                logger.debug(f"Found member: {name}, type: {type(member).__name__}")

                # Only include functions defined in this module (not imported)
                if inspect.isfunction(member):
                    logger.debug(f"Member {name} is a function. Module: {member.__module__}, Expected: {module.__name__}")

                    if member.__module__ == module.__name__:
                        # Skip private functions (starting with underscore)
                        if name.startswith("_") and not (name.startswith("__") and name.endswith("__")):
                            logger.debug(f"Skipping private function: {name} in {file_path}")
                            continue

                        if not function_name_set or name in function_name_set:
                            logger.debug(f"Adding function {name} to discovered functions")
                            module_functions.append((member, name))

                            if function_name_set and name in function_name_set:
                                function_name_set.remove(name)
                    else:
                        logger.debug(f"Skipping function {name} because it's not defined in this module")

            if module_functions:
                logger.info(f"Found {len(module_functions)} function(s) in {file_path}")
                for func, name in module_functions:
                    discovered_functions.append((func, name, file_path))
            else:
                logger.warning(f"No suitable functions found in {file_path}")
        else:
            logger.warning(f"Failed to load module from {file_path}")

    if function_name_set and len(function_name_set) > 0:
        logger.warning(f"Could not find the following specified functions: {list(function_name_set)}")

    return discovered_functions


def extract_docstring_description(func: Callable) -> str:
    """
    Extract a description from a function's docstring.

    Args:
        func: The function to extract the docstring from.

    Returns:
        A string containing the function description.
    """
    docstring = inspect.getdoc(func)
    if not docstring:
        return "No description available"

    # Extract the first paragraph as the description
    description = docstring.strip().split("\n\n")[0].replace("\n", " ")
    return description


def _type_to_json_schema_type(python_type: type) -> str | dict[str, Any]:
    """
    Convert Python type to JSON Schema type.

    Args:
        python_type: Python type annotation

    Returns:
        JSON Schema type string or object
    """
    # Handle basic types
    if python_type is str:
        return "string"
    elif python_type is int:
        return "integer"
    elif python_type is float:
        return "number"
    elif python_type is bool:
        return "boolean"
    elif python_type is list:
        return {"type": "array"}
    elif python_type is dict:
        return {"type": "object"}
    elif python_type is None or python_type is type(None):
        return "null"

    # Complex types
    origin = getattr(python_type, "__origin__", None)
    if origin:
        if origin is list:
            args = getattr(python_type, "__args__", [])
            if args:
                item_type = _type_to_json_schema_type(args[0])
                return {
                    "type": "array",
                    "items": item_type if isinstance(item_type, dict) else {"type": item_type}
                }
            return {"type": "array"}

        elif origin is dict:
            return {"type": "object"}

        elif origin is Union:
            args = getattr(python_type, "__args__", [])
            if len(args) == 2 and type(None) in args:  # Optional type
                non_none_type = next(arg for arg in args if arg is not type(None))
                schema_type = _type_to_json_schema_type(non_none_type)
                if isinstance(schema_type, dict):
                    return schema_type  # Already a schema object
                return {"type": schema_type}
            else:
                types = [_type_to_json_schema_type(arg) for arg in args]
                return {"anyOf": [{"type": t} if isinstance(t, str) else t for t in types]}

    # Fallback
    return "string"


def generate_schema_for_function(func: Callable) -> dict[str, Any]:
    """
    Generate a JSON Schema for a Python function.

    Args:
        func: The function to generate schema for

    Returns:
        Dictionary containing the JSON Schema
    """
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Extract docstring for overall description
    description = extract_docstring_description(func)

    # Build parameter schema
    properties = {}
    required = []

    for param_name, param in signature.parameters.items():
        # Skip self, cls parameters
        if param_name in ("self", "cls"):
            continue

        param_type = type_hints.get(param_name, Any)
        param_schema = {"description": f"Parameter '{param_name}'"}

        # Add type information
        json_schema_type = _type_to_json_schema_type(param_type)
        if isinstance(json_schema_type, str):
            param_schema["type"] = json_schema_type
        else:
            param_schema.update(json_schema_type)

        # Add default value if present
        if param.default is not param.empty:
            if param.default is not None:  # Don't add null defaults
                param_schema["default"] = param.default
        else:
            required.append(param_name)

        properties[param_name] = param_schema

    # Build return type schema
    return_type = type_hints.get("return", Any)
    output_schema = {
        "type": "object",
        "properties": {
            "result": _type_to_json_schema_type(return_type)
        }
    }

    # Combine into a complete schema
    schema = {
        "name": func.__name__,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required
        },
        "output_schema": output_schema,
        "version": "1.0.0"
    }

    return schema


def generate_typer_wrapper(
    script_path: Path,
    function_name: str,
    schema: dict[str, Any],
    output_dir: Path
) -> Path:
    """
    Generate a Typer CLI wrapper for a Python function.

    Args:
        script_path: Path to the original Python script
        function_name: Name of the function to wrap
        schema: JSON Schema for the function
        output_dir: Directory to save the wrapper

    Returns:
        Path to the generated wrapper script
    """
    wrapper_id = f"{script_path.stem}_{function_name}"
    wrapper_file = output_dir / f"{wrapper_id}_wrapper.py"

    wrapper_content = [
        "#!/usr/bin/env python",
        f'"""Typer CLI wrapper for {function_name} function from {script_path.name}"""',
        "",
        "import sys",
        "import json",
        "import importlib.util",
        "from pathlib import Path",
        "import typer",
        "",
        "# Create Typer app",
        "app = typer.Typer()",
        "",
        "def load_function():",
        f'    script_path = Path(r"{script_path}")',
        "    module_name = script_path.stem",
        "    spec = importlib.util.spec_from_file_location(module_name, script_path)",
        "    if not spec or not spec.loader:",
        '        print(f"Could not load module from {script_path}", file=sys.stderr)',
        "        sys.exit(1)",
        "    module = importlib.util.module_from_spec(spec)",
        "    spec.loader.exec_module(module)",
        f'    if not hasattr(module, "{function_name}"):',
        f'        print(f"Module does not contain function: {function_name}", file=sys.stderr)',
        "        sys.exit(1)",
        f'    return getattr(module, "{function_name}")',
        "",
        "@app.command()",
        "def main(",
    ]

    # Add function parameters
    properties = schema["input_schema"]["properties"]
    required = schema["input_schema"].get("required", [])

    for param_name, param_schema in properties.items():
        param_type = param_schema.get("type", "string")
        is_required = param_name in required
        has_default = "default" in param_schema

        # Convert JSON Schema type to Python type
        if param_type == "string":
            py_type = "str"
        elif param_type == "integer":
            py_type = "int"
        elif param_type == "number":
            py_type = "float"
        elif param_type == "boolean":
            py_type = "bool"
        else:
            py_type = "str"  # Default to string for complex types

        # Build parameter definition
        param_def = f"    {param_name}: {py_type}"

        if not is_required:
            if has_default:
                default_value = param_schema["default"]
                if param_type == "string":
                    param_def += f' = "{default_value}"'
                else:
                    param_def += f" = {default_value}"
            else:
                param_def += " = None"

        param_def += ","
        wrapper_content.append(param_def)

    # Close parameter list and add function body
    wrapper_content.extend([
        "):",
        '    """CLI wrapper for the function"""',
        "    func = load_function()",
        "    try:",
        "        # Call the function with provided arguments",
        "        result = func(",
    ])

    # Add function arguments
    for param_name in properties.keys():
        wrapper_content.append(f"            {param_name}={param_name},")

    wrapper_content.extend([
        "        )",
        "        # Output the result as JSON",
        '        print(json.dumps({"result": result}, default=str))',
        "    except Exception as e:",
        '        print(json.dumps({"error": str(e)}), file=sys.stderr)',
        "        sys.exit(1)",
        "",
        "",
        'if __name__ == "__main__":',
        "    app()",
    ])

    # Write wrapper file
    with open(wrapper_file, "w", encoding="utf-8") as f:
        f.write("\n".join(wrapper_content))

    # Make executable
    wrapper_file.chmod(wrapper_file.stat().st_mode | 0o755)

    return wrapper_file


def create_tool_metadata_file(
    script_path: Path,
    function_name: str,
    schema: dict[str, Any],
    wrapper_path: Path,
    output_dir: Path
) -> Path:
    """
    Create a metadata file for MCP tool registration.

    Args:
        script_path: Path to the original Python script
        function_name: Name of the function to wrap
        schema: JSON Schema for the function
        wrapper_path: Path to the generated wrapper script
        output_dir: Directory to save the metadata

    Returns:
        Path to the generated metadata file
    """
    tool_id = f"{script_path.stem}_{function_name}"
    metadata_file = output_dir / f"{tool_id}.json"

    # Create tool metadata
    metadata = {
        "tool_id": tool_id,
        "name": function_name,
        "description": schema["description"],
        "version": schema["version"],
        "input_schema": schema["input_schema"],
        "output_schema": schema["output_schema"],
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
