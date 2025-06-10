"""HTTP client for communicating with the FastAPI backend."""

import logging
from typing import Any, Dict, List, Optional, Union
import httpx
import json

logger = logging.getLogger(__name__)


class APIClient:
    """HTTP client for FastAPI backend communication."""
    
    def __init__(self, base_url: str = "http://localhost:8090"):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the FastAPI backend
        """
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    # ——— Health and Status ———
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the FastAPI backend."""
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    # ——— File Management ———
    
    def upload_script(self, file_path: str) -> Dict[str, Any]:
        """Upload a Python script file.
        
        Args:
            file_path: Path to the Python file to upload
            
        Returns:
            Upload response with script metadata
        """
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path, f, "text/x-python")}
                response = self.client.post("/api/v1/upload_script", files=files)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Script upload failed: {e}")
            raise
    
    def list_scripts(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List uploaded scripts.
        
        Args:
            limit: Maximum number of scripts to return
            offset: Number of scripts to skip
            
        Returns:
            List of script metadata
        """
        try:
            params = {"limit": limit, "offset": offset}
            response = self.client.get("/api/v1/scripts", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list scripts: {e}")
            return {"scripts": [], "total": 0, "error": str(e)}
    
    def get_script(self, script_id: str) -> Dict[str, Any]:
        """Get script metadata by ID.
        
        Args:
            script_id: Unique script identifier
            
        Returns:
            Script metadata
        """
        try:
            response = self.client.get(f"/api/v1/scripts/{script_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get script {script_id}: {e}")
            return {"error": str(e)}
    
    def delete_script(self, script_id: str) -> Dict[str, Any]:
        """Delete a script.
        
        Args:
            script_id: Unique script identifier
            
        Returns:
            Deletion result
        """
        try:
            response = self.client.delete(f"/api/v1/scripts/{script_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to delete script {script_id}: {e}")
            return {"error": str(e)}
    
    def discover_tools(self, script_id: str) -> Dict[str, Any]:
        """Discover tools in a script.

        Args:
            script_id: Unique script identifier

        Returns:
            Tool discovery results
        """
        try:
            response = self.client.get(f"/api/v1/scripts/{script_id}/discover")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Tool discovery failed for {script_id}: {e}")
            return {"error": str(e)}
    
    # ——— Service Management ———
    
    def list_services(self) -> Dict[str, Any]:
        """List all registered services."""
        try:
            response = self.client.get("/api/v1/services")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list services: {e}")
            return {"services": [], "error": str(e)}
    
    def get_service(self, service_id: str) -> Dict[str, Any]:
        """Get service details by ID.
        
        Args:
            service_id: Unique service identifier
            
        Returns:
            Service details
        """
        try:
            response = self.client.get(f"/api/v1/services/{service_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get service {service_id}: {e}")
            return {"error": str(e)}
    
    def create_service(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new service.
        
        Args:
            service_config: Service configuration
            
        Returns:
            Created service details
        """
        try:
            response = self.client.post("/api/v1/services", json=service_config)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create service: {e}")
            return {"error": str(e)}
    
    def update_service(self, service_id: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing service.
        
        Args:
            service_id: Unique service identifier
            service_config: Updated service configuration
            
        Returns:
            Updated service details
        """
        try:
            response = self.client.put(f"/api/v1/services/{service_id}", json=service_config)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to update service {service_id}: {e}")
            return {"error": str(e)}
    
    def delete_service(self, service_id: str) -> Dict[str, Any]:
        """Delete a service.
        
        Args:
            service_id: Unique service identifier
            
        Returns:
            Deletion result
        """
        try:
            response = self.client.delete(f"/api/v1/services/{service_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to delete service {service_id}: {e}")
            return {"error": str(e)}
    
    def get_service_health(self, service_id: str) -> Dict[str, Any]:
        """Get service health status.
        
        Args:
            service_id: Unique service identifier
            
        Returns:
            Service health information
        """
        try:
            response = self.client.get(f"/api/v1/services/{service_id}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get service health for {service_id}: {e}")
            return {"status": "error", "error": str(e)}


# Global API client instance
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get the global API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client


def close_api_client():
    """Close the global API client."""
    global _api_client
    if _api_client is not None:
        _api_client.close()
        _api_client = None
