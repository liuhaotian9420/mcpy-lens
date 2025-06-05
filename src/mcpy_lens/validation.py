"""
Script validation utilities for mcpy-lens.

This module provides functions for validating Python scripts to determine
if they're suitable for different hosting modes.
"""

import ast
from pathlib import Path


def validate_script_entry_point(script_path: Path) -> bool:
    """
    Validate if a Python script has an if __name__ == "__main__" block.

    Args:
        script_path: Path to the Python script

    Returns:
        True if the script has an entry point, False otherwise
    """
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    with open(script_path, encoding='utf-8') as f:
        script_content = f.read()    # Parse the Python code to AST
    try:
        tree = ast.parse(script_content)
        for node in tree.body:
            # Look for if statements at the module level
            if isinstance(node, ast.If):
                # Check if it's an if __name__ == "__main__" block
                test = node.test
                if (isinstance(test, ast.Compare) and
                    isinstance(test.left, ast.Name) and test.left.id == "__name__" and
                    len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) and
                    len(test.comparators) == 1 and
                    isinstance(test.comparators[0], ast.Constant) and
                    test.comparators[0].value == "__main__"):
                    return True
        return False
    except SyntaxError:
        return False


def extract_main_block_arguments(script_path: Path) -> list[tuple[str, str, object | None]]:
    """
    Extract command-line arguments used in the __main__ block of a script.

    This function analyzes the __main__ block to identify potential command-line arguments
    by looking for patterns like argparse usage or sys.argv access.

    Args:
        script_path: Path to the Python script

    Returns:
        List of tuples (arg_name, arg_type, default_value) for identified arguments
    """
    if not validate_script_entry_point(script_path):
        return []

    with open(script_path, encoding='utf-8') as f:
        script_content = f.read()

    arguments = []
    argparse_imports = set()

    # Parse the Python code to AST
    try:
        tree = ast.parse(script_content)

        # Check for relevant imports first
        for node in tree.body:
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name == 'argparse':
                        argparse_imports.add(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module == 'argparse':
                    for name in node.names:
                        argparse_imports.add(f"argparse.{name.name}")

        # Find the main block
        main_block = None
        for node in tree.body:
            if isinstance(node, ast.If):
                test = node.test
                if (isinstance(test, ast.Compare) and
                    isinstance(test.left, ast.Name) and test.left.id == "__name__" and
                    len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) and
                    len(test.comparators) == 1 and
                    isinstance(test.comparators[0], ast.Constant) and
                    test.comparators[0].value == "__main__"):
                    main_block = node
                    break

        if not main_block:
            return []

        # Look for argparse usage in the main block
        if argparse_imports:
            arguments.extend(_extract_argparse_arguments(main_block))

        # Look for sys.argv usage as fallback
        if not arguments:
            arguments.extend(_extract_sys_argv_usage(main_block))

        return arguments

    except SyntaxError:
        return []


def _extract_argparse_arguments(main_block: ast.If) -> list[tuple[str, str, object | None]]:
    """
    Extract arguments defined with argparse in the main block.

    Args:
        main_block: AST node for the if __name__ == "__main__" block

    Returns:
        List of (arg_name, arg_type, default_value) tuples
    """
    arguments = []
    parser_var = None

    # Find the parser definition (argparse.ArgumentParser())
    for node in ast.walk(main_block):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    call = node.value
                    if _is_argparse_constructor(call):
                        parser_var = target.id
                        break

    if not parser_var:
        return []

    # Find add_argument calls on the parser
    for node in ast.walk(main_block):
        if (isinstance(node, ast.Call) and
            isinstance(node.func, ast.Attribute) and
            node.func.attr == "add_argument" and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == parser_var):

            arg_name = None
            arg_type = "string"  # Default type
            default_value = None

            # Get the argument name
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith('--'):
                        arg_name = arg.value[2:]
                        break

            # Check keywords for type and default
            for kw in node.keywords:
                if kw.arg == "type":
                    if isinstance(kw.value, ast.Name):
                        if kw.value.id == "int":
                            arg_type = "integer"
                        elif kw.value.id == "float":
                            arg_type = "number"
                        elif kw.value.id == "bool":
                            arg_type = "boolean"
                elif kw.arg == "default" and isinstance(kw.value, ast.Constant):
                    default_value = kw.value.value
                elif kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                    arg_name = kw.value.value

            if arg_name:
                arguments.append((arg_name, arg_type, default_value))

    return arguments


def _is_argparse_constructor(call_node: ast.Call) -> bool:
    """Check if a call node is an argparse.ArgumentParser constructor."""
    if isinstance(call_node.func, ast.Attribute):
        return (call_node.func.attr == "ArgumentParser" and
                isinstance(call_node.func.value, ast.Name) and
                call_node.func.value.id == "argparse")
    elif isinstance(call_node.func, ast.Name):
        return call_node.func.id == "ArgumentParser"
    return False


def _extract_sys_argv_usage(main_block: ast.If) -> list[tuple[str, str, object | None]]:
    """
    Look for sys.argv usage patterns in the main block.
    This is a fallback when argparse is not used.

    Args:
        main_block: AST node for the if __name__ == "__main__" block

    Returns:
        List of (arg_name, arg_type, default_value) tuples
    """
    # This is a simplified implementation that looks for common patterns
    # A real implementation would need more sophisticated analysis
    arguments = []
    sys_argv_uses = set()

    # Find sys.argv accesses
    for node in ast.walk(main_block):
        if (isinstance(node, ast.Subscript) and
            isinstance(node.value, ast.Attribute) and
            node.value.attr == "argv" and
            isinstance(node.value.value, ast.Name) and
            node.value.value.id == "sys"):

            # Check if it's a simple index like sys.argv[1]
            if isinstance(node.slice, ast.Index) and isinstance(node.slice.value, ast.Constant):
                index = node.slice.value.value
                if isinstance(index, int) and index > 0:
                    sys_argv_uses.add(index)

    # For each index used, create a generic argument entry
    for index in sorted(sys_argv_uses):
        arg_name = f"arg{index}"
        arg_type = "string"  # Default to string
        arguments.append((arg_name, arg_type, None))

    return arguments
