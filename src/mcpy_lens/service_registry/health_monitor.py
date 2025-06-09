"""
Health monitoring for registered services.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess

from .models import ServiceConfig, ServiceStatus, HealthCheckResult
from .service_registry import ServiceRegistry


class HealthMonitor:
    """Monitors health of registered services with functional testing."""
    
    def __init__(self, service_registry: ServiceRegistry, wrappers_dir: Path):
        self.service_registry = service_registry
        self.wrappers_dir = wrappers_dir
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._health_results: Dict[str, HealthCheckResult] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 60  # Check every minute
        self._started = False
    
    async def start(self) -> None:
        """Start health monitoring."""
        if self._started:
            return
        
        self.logger.info("Starting health monitoring")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._started = True
    
    async def stop(self) -> None:
        """Stop health monitoring."""
        if not self._started:
            return
        
        self.logger.info("Stopping health monitoring")
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self._started = False
    
    async def check_service_health(self, service_id: str) -> HealthCheckResult:
        """Perform health check on a specific service."""
        service_config = self.service_registry.get_service(service_id)
        if not service_config:
            return HealthCheckResult(
                service_id=service_id,
                status=ServiceStatus.ERROR,
                timestamp=time.time(),
                response_time_ms=0,
                error_message="Service not found"
            )
        
        start_time = time.time()
        
        try:
            # Perform functional health check
            if service_config.hosting_mode.value == "stdio":
                result = await self._check_stdio_service(service_config)
            else:
                result = await self._check_sse_service(service_config)
            
            response_time = (time.time() - start_time) * 1000
            
            health_result = HealthCheckResult(
                service_id=service_id,
                status=result["status"],
                timestamp=time.time(),
                response_time_ms=response_time,
                details=result.get("details", {}),
                error_message=result.get("error")
            )
            
            # Update service status if it changed
            if service_config.status != result["status"]:
                await self.service_registry.update_service_status(service_id, result["status"])
            
            # Store health result
            self._health_results[service_id] = health_result
            
            return health_result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_message = str(e)
            
            health_result = HealthCheckResult(
                service_id=service_id,
                status=ServiceStatus.ERROR,
                timestamp=time.time(),
                response_time_ms=response_time,
                error_message=error_message
            )
            
            # Update service status to error
            await self.service_registry.update_service_status(service_id, ServiceStatus.ERROR)
            
            # Store health result
            self._health_results[service_id] = health_result
            
            self.logger.error(f"Health check failed for service {service_id}: {error_message}")
            return health_result
    
    async def _check_stdio_service(self, service_config: ServiceConfig) -> Dict[str, Any]:
        """Check health of a STDIO-based service."""
        # Find wrapper path
        wrapper_path = self._get_wrapper_path(service_config)
        if not wrapper_path or not wrapper_path.exists():
            return {
                "status": ServiceStatus.ERROR,
                "error": f"Wrapper not found: {wrapper_path}"
            }
        
        try:
            # Test basic functionality by calling listtools
            test_request = {
                "jsonrpc": "2.0",
                "method": "listtools",
                "id": "health_check"
            }
            
            # Execute wrapper with test request
            process = await asyncio.create_subprocess_exec(
                "python", str(wrapper_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=wrapper_path.parent
            )
            
            # Send test request
            request_json = json.dumps(test_request) + "\n"
            stdout, stderr = await asyncio.wait_for(
                process.communicate(request_json.encode()),
                timeout=10.0
            )
            
            if process.returncode != 0:
                return {
                    "status": ServiceStatus.ERROR,
                    "error": f"Wrapper process failed: {stderr.decode()}"
                }
            
            # Parse response
            try:
                response = json.loads(stdout.decode().strip())
                if "result" in response:
                    return {
                        "status": ServiceStatus.ACTIVE,
                        "details": {
                            "tools_count": len(response["result"].get("tools", [])),
                            "response": response
                        }
                    }
                else:
                    return {
                        "status": ServiceStatus.ERROR,
                        "error": f"Invalid response: {response}"
                    }
            except json.JSONDecodeError as e:
                return {
                    "status": ServiceStatus.ERROR,
                    "error": f"Invalid JSON response: {e}"
                }
                
        except asyncio.TimeoutError:
            return {
                "status": ServiceStatus.ERROR,
                "error": "Health check timed out"
            }
        except Exception as e:
            return {
                "status": ServiceStatus.ERROR,
                "error": f"Health check failed: {str(e)}"
            }
    
    async def _check_sse_service(self, service_config: ServiceConfig) -> Dict[str, Any]:
        """Check health of an SSE-based service."""
        # For SSE services, we check if the wrapper exists and is valid
        # The actual SSE functionality is handled by the adapter layer
        wrapper_path = self._get_wrapper_path(service_config)
        if not wrapper_path or not wrapper_path.exists():
            return {
                "status": ServiceStatus.ERROR,
                "error": f"Wrapper not found: {wrapper_path}"
            }
        
        # Check if metadata file exists
        metadata_path = wrapper_path.parent / f"{service_config.script_id}_metadata.json"
        if not metadata_path.exists():
            return {
                "status": ServiceStatus.ERROR,
                "error": f"Metadata file not found: {metadata_path}"
            }
        
        try:
            # Validate metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if "tools" not in metadata:
                return {
                    "status": ServiceStatus.ERROR,
                    "error": "Invalid metadata: missing tools"
                }
            
            return {
                "status": ServiceStatus.ACTIVE,
                "details": {
                    "tools_count": len(metadata["tools"]),
                    "wrapper_path": str(wrapper_path),
                    "metadata_path": str(metadata_path)
                }
            }
            
        except Exception as e:
            return {
                "status": ServiceStatus.ERROR,
                "error": f"Metadata validation failed: {str(e)}"
            }
    
    def _get_wrapper_path(self, service_config: ServiceConfig) -> Optional[Path]:
        """Get wrapper path for a service."""
        wrapper_dir = self.wrappers_dir / service_config.script_id
        if wrapper_dir.exists():
            wrapper_script = wrapper_dir / f"{service_config.script_id}_wrapper.py"
            if wrapper_script.exists():
                return wrapper_script
        return None
    
    def get_health_result(self, service_id: str) -> Optional[HealthCheckResult]:
        """Get latest health check result for a service."""
        return self._health_results.get(service_id)
    
    def get_all_health_results(self) -> Dict[str, HealthCheckResult]:
        """Get all health check results."""
        return self._health_results.copy()
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                # Get all active services
                active_services = self.service_registry.get_active_services()
                
                # Check health of each service
                for service_config in active_services:
                    try:
                        await self.check_service_health(service_config.service_id)
                    except Exception as e:
                        self.logger.error(f"Error checking health for service {service_config.service_id}: {e}")
                
                # Wait for next check
                await asyncio.sleep(self._monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
