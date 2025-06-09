"""
Process management for MCP adapter.
"""

import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, AsyncIterator
import json

from .config import AdapterConfig


@dataclass
class ProcessInfo:
    """Information about a running wrapper process."""
    process: subprocess.Popen
    wrapper_path: Path
    created_at: float
    last_used: float
    request_count: int = 0
    
    def is_alive(self) -> bool:
        """Check if process is still alive."""
        return self.process.poll() is None
    
    def update_usage(self) -> None:
        """Update usage statistics."""
        self.last_used = time.time()
        self.request_count += 1


class ProcessManager:
    """Manages wrapper processes for on-demand execution."""
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._processes: Dict[str, ProcessInfo] = {}
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the process manager."""
        self.logger.info("Starting process manager")
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self) -> None:
        """Stop the process manager and clean up all processes."""
        self.logger.info("Stopping process manager")
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Terminate all processes
        for process_id, process_info in self._processes.items():
            await self._terminate_process(process_id, process_info)
        
        self._processes.clear()
    
    async def execute_request(
        self,
        wrapper_path: Path,
        request_data: Dict,
        request_id: str
    ) -> AsyncIterator[Dict]:
        """Execute a request using a wrapper process."""
        async with self._semaphore:
            process_info = None
            try:
                # Spawn new process for on-demand execution
                process_info = await self._spawn_process(wrapper_path, request_id)
                
                # Send request to process
                await self._send_request(process_info, request_data)
                
                # Read and yield responses
                async for response in self._read_responses(process_info, request_id):
                    yield response
                    
            except Exception as e:
                self.logger.error(f"Error executing request {request_id}: {e}")
                yield {
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
            finally:
                # Clean up process after request completion
                if process_info:
                    await self._terminate_process(request_id, process_info)
                    self._processes.pop(request_id, None)
    
    async def _spawn_process(self, wrapper_path: Path, process_id: str) -> ProcessInfo:
        """Spawn a new wrapper process."""
        try:
            # Create the subprocess
            process = await asyncio.create_subprocess_exec(
                "python", str(wrapper_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=wrapper_path.parent
            )
            
            current_time = time.time()
            process_info = ProcessInfo(
                process=process,
                wrapper_path=wrapper_path,
                created_at=current_time,
                last_used=current_time
            )
            
            self._processes[process_id] = process_info
            self.logger.debug(f"Spawned process {process_id} for wrapper {wrapper_path}")
            
            return process_info
            
        except Exception as e:
            self.logger.error(f"Failed to spawn process for {wrapper_path}: {e}")
            raise
    
    async def _send_request(self, process_info: ProcessInfo, request_data: Dict) -> None:
        """Send a JSON-RPC request to the process."""
        try:
            request_json = json.dumps(request_data) + "\n"
            process_info.process.stdin.write(request_json.encode())
            await process_info.process.stdin.drain()
            process_info.update_usage()
            
        except Exception as e:
            self.logger.error(f"Failed to send request to process: {e}")
            raise
    
    async def _read_responses(
        self, 
        process_info: ProcessInfo, 
        request_id: str
    ) -> AsyncIterator[Dict]:
        """Read responses from the process stdout."""
        try:
            while True:
                # Read line with timeout
                try:
                    line_bytes = await asyncio.wait_for(
                        process_info.process.stdout.readline(),
                        timeout=self.config.process_timeout
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(f"Process {request_id} timed out")
                    yield {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Request timed out"
                        }
                    }
                    break
                
                if not line_bytes:
                    # Process ended
                    break
                
                try:
                    line = line_bytes.decode().strip()
                    if line:
                        response = json.loads(line)
                        yield response
                        
                        # Check if this is the final response
                        if not response.get("partial", False):
                            break
                            
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON from process {request_id}: {line}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error reading from process {request_id}: {e}")
            yield {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Process communication error: {str(e)}"
                }
            }
    
    async def _terminate_process(self, process_id: str, process_info: ProcessInfo) -> None:
        """Terminate a process gracefully."""
        try:
            if process_info.process.stdin:
                process_info.process.stdin.close()
            
            # Wait for process to terminate gracefully
            try:
                await asyncio.wait_for(process_info.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Force kill if it doesn't terminate gracefully
                process_info.process.kill()
                await process_info.process.wait()
            
            self.logger.debug(f"Terminated process {process_id}")
            
        except Exception as e:
            self.logger.error(f"Error terminating process {process_id}: {e}")
    
    def get_process_stats(self) -> Dict[str, int]:
        """Get process statistics."""
        active_processes = len(self._processes)
        total_requests = sum(p.request_count for p in self._processes.values())
        
        return {
            "active_processes": active_processes,
            "total_requests_processed": total_requests,
            "max_concurrent": self.config.max_concurrent_requests,
            "available_slots": self._semaphore._value
        }
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up stale processes."""
        while True:
            try:
                await asyncio.sleep(self.config.process_cleanup_interval)
                await self._cleanup_stale_processes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in process cleanup loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_stale_processes(self) -> None:
        """Clean up processes that are no longer alive."""
        stale_processes = []
        
        for process_id, process_info in self._processes.items():
            if not process_info.is_alive():
                stale_processes.append(process_id)
        
        for process_id in stale_processes:
            process_info = self._processes.pop(process_id, None)
            if process_info:
                await self._terminate_process(process_id, process_info)
        
        if stale_processes:
            self.logger.info(f"Cleaned up {len(stale_processes)} stale processes")
