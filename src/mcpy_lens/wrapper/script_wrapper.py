"""
Script wrapper implementation for executing Python scripts and functions.
"""

import json
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncIterator
import tempfile
import sys

from .base import WrapperBase
from .json_rpc import JSONRPCRequest, JSONRPCError
from .config import WrapperConfig

logger = logging.getLogger(__name__)


class ScriptWrapper(WrapperBase):
    """Wrapper for executing Python scripts and their functions."""
    
    def __init__(
        self, 
        script_path: Path, 
        metadata_path: Path, 
        config: Optional[WrapperConfig] = None
    ):
        super().__init__(config)
        self.script_path = script_path
        self.metadata_path = metadata_path
        self.metadata = self._load_metadata()
        
        # Logger for script execution (full transparency)
        self.script_logger = logging.getLogger("mcpy_lens.wrapper.script_execution")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load tool metadata from file."""
        try:
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {str(e)}")
            return {"tools": [], "script_info": {}}
    
    async def _handle_list_tools(self, request: JSONRPCRequest):
        """Handle list tools requests."""
        tools = self.metadata.get("tools", [])
        
        # Format tools for MCP response
        tool_list = []
        for tool in tools:
            tool_info = {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("input_schema", {}),
            }
            tool_list.append(tool_info)
        
        response = self.json_rpc.create_response(request.id, {"tools": tool_list})
        await self._send_response(response)
    
    async def _handle_get_tool_info(self, request: JSONRPCRequest):
        """Handle get tool info requests."""
        params = request.params or {}
        tool_name = params.get("name")
        
        if not tool_name:
            response = self.json_rpc.create_error_response(
                request.id, JSONRPCError.INVALID_PARAMS, "Missing tool name"
            )
            await self._send_response(response)
            return
        
        # Find tool in metadata
        tool = None
        for t in self.metadata.get("tools", []):
            if t.get("name") == tool_name:
                tool = t
                break
        
        if not tool:
            response = self.json_rpc.create_error_response(
                request.id, JSONRPCError.METHOD_NOT_FOUND, f"Tool '{tool_name}' not found"
            )
            await self._send_response(response)
            return
        
        tool_info = {
            "name": tool.get("name"),
            "description": tool.get("description", ""),
            "inputSchema": tool.get("input_schema", {}),
            "outputSchema": tool.get("output_schema", {}),
        }
        
        response = self.json_rpc.create_response(request.id, tool_info)
        await self._send_response(response)
    
    async def _handle_call_tool(self, request: JSONRPCRequest):
        """Handle call tool requests."""
        params = request.params or {}
        tool_name = params.get("name")
        tool_arguments = params.get("arguments", {})
        
        if not tool_name:
            response = self.json_rpc.create_error_response(
                request.id, JSONRPCError.INVALID_PARAMS, "Missing tool name"
            )
            await self._send_response(response)
            return
        
        # Find tool in metadata
        tool = None
        for t in self.metadata.get("tools", []):
            if t.get("name") == tool_name:
                tool = t
                break
        
        if not tool:
            response = self.json_rpc.create_error_response(
                request.id, JSONRPCError.METHOD_NOT_FOUND, f"Tool '{tool_name}' not found"
            )
            await self._send_response(response)
            return
        
        # Execute the tool
        try:
            async for result in self._execute_tool(tool, tool_arguments, request.id):
                await self._send_response(result)
        except Exception as e:
            self.script_logger.exception(f"Tool execution failed: {e}")  # Full transparency
            response = self.json_rpc.create_error_response(
                request.id, 
                JSONRPCError.EXECUTION_ERROR,
                {"error": str(e), "tool": tool_name}
            )
            await self._send_response(response)

    async def _execute_tool(
        self,
        tool: Dict[str, Any],
        arguments: Dict[str, Any],
        request_id: Optional[str]
    ) -> AsyncIterator[Any]:
        """Execute a tool and yield streaming results."""

        # Create a temporary script that calls the specific function
        execution_script = self._create_execution_script(tool, arguments)

        try:
            # Execute the script in a subprocess
            async for result in self._run_subprocess(execution_script, request_id):
                yield result

        except asyncio.TimeoutError:
            yield self.json_rpc.create_error_response(
                request_id, JSONRPCError.TIMEOUT_ERROR
            )
        except Exception as e:
            self.script_logger.exception(f"Subprocess execution failed: {e}")
            yield self.json_rpc.create_error_response(
                request_id, JSONRPCError.EXECUTION_ERROR, str(e)
            )

    def _create_execution_script(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> str:
        """Create a Python script that executes the specific function."""
        function_name = tool.get("name")

        # Create the execution script
        script_content = f'''
import sys
import json
import traceback
from pathlib import Path

# Add the script directory to Python path
script_dir = Path("{self.script_path}").parent
sys.path.insert(0, str(script_dir))

try:
    # Import the original script as a module
    import importlib.util
    spec = importlib.util.spec_from_file_location("user_script", "{self.script_path}")
    user_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_module)

    # Get the function
    if hasattr(user_module, "{function_name}"):
        func = getattr(user_module, "{function_name}")

        # Parse arguments
        arguments = {json.dumps(arguments)}

        # Call the function
        result = func(**arguments)

        # Output the result
        output = {{
            "success": True,
            "result": result,
            "function": "{function_name}"
        }}
        print(json.dumps(output))

    else:
        error_output = {{
            "success": False,
            "error": "Function '{function_name}' not found in script",
            "function": "{function_name}"
        }}
        print(json.dumps(error_output))
        sys.exit(1)

except Exception as e:
    error_output = {{
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc(),
        "function": "{function_name}"
    }}
    print(json.dumps(error_output))
    sys.exit(1)
'''
        return script_content

    async def _run_subprocess(
        self,
        script_content: str,
        request_id: Optional[str]
    ) -> AsyncIterator[Any]:
        """Run the execution script in a subprocess with streaming output."""

        # Create temporary file for the execution script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script_path = f.name

        try:
            # Prepare subprocess command
            cmd = [
                self.config.python_executable,
                temp_script_path
            ]

            # Start subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.config.get_subprocess_env(),
                cwd=self.config.working_directory or self.script_path.parent
            )

            # Stream output with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.max_execution_time
                )

                # Process the output
                if process.returncode == 0:
                    # Success - parse the JSON output
                    try:
                        result_data = json.loads(stdout.decode('utf-8'))
                        yield self.json_rpc.create_response(request_id, result_data)
                    except json.JSONDecodeError:
                        # If not JSON, return raw output
                        yield self.json_rpc.create_response(
                            request_id,
                            {"output": stdout.decode('utf-8'), "raw": True}
                        )
                else:
                    # Error - return error information
                    error_info = {
                        "returncode": process.returncode,
                        "stdout": stdout.decode('utf-8') if stdout else "",
                        "stderr": stderr.decode('utf-8') if stderr else ""
                    }
                    yield self.json_rpc.create_error_response(
                        request_id, JSONRPCError.EXECUTION_ERROR, error_info
                    )

            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                raise

        finally:
            # Clean up temporary file
            try:
                Path(temp_script_path).unlink()
            except Exception as e:
                self.logger.error(f"Failed to clean up temp file: {e}")
