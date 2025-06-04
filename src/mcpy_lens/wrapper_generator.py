def generate_file_typer_wrapper(script_path, script_id, output_dir, script_args=None):
    """Generate wrapper for entire file"""
    return output_dir / f"{script_id}_wrapper.py"

def create_tool_metadata_file(script_path, script_id, wrapper_path, script_args, output_dir, description=""):
    """Create metadata file for tool"""
    return output_dir / f"{script_id}.json"

