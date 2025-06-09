"""
Integration tests for Stage 6 service registry implementation.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpy_lens.service_registry.service_registry import ServiceRegistry
from mcpy_lens.service_registry.service_manager import ServiceManager
from mcpy_lens.service_registry.health_monitor import HealthMonitor
from mcpy_lens.service_registry.models import (
    ServiceConfig, ServiceStatus, ServiceRegistrationRequest, ToolInfo, ServiceType, HostingMode
)
from mcpy_lens.routing import RouteManager


def test_service_registry_models():
    """Test service registry data models."""
    print("🔧 Testing service registry models...")
    
    try:
        # Test ToolInfo
        tool = ToolInfo(
            name="test_tool",
            description="A test tool",
            parameters={"param1": "string"},
            return_type="string"
        )
        
        tool_dict = tool.to_dict()
        assert tool_dict["name"] == "test_tool"
        
        tool_from_dict = ToolInfo.from_dict(tool_dict)
        assert tool_from_dict.name == tool.name
        
        # Test ServiceConfig
        service_config = ServiceConfig(
            service_id="test-service",
            name="Test Service",
            description="A test service",
            service_type=ServiceType.FUNCTION,
            hosting_mode=HostingMode.SSE,
            script_id="test-script",
            tools=[tool],
            routes=["/api/test"]
        )
        
        config_dict = service_config.to_dict()
        assert config_dict["service_id"] == "test-service"
        assert config_dict["status"] == "inactive"
        
        config_from_dict = ServiceConfig.from_dict(config_dict)
        assert config_from_dict.service_id == service_config.service_id
        
        print("✅ Service registry models working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Service registry models test failed: {e}")
        return False


async def test_service_registry():
    """Test service registry functionality."""
    print("\n📋 Testing service registry...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            services_dir = Path(temp_dir) / "services"
            services_dir.mkdir()
            
            registry = ServiceRegistry(services_dir)
            
            # Test service registration
            tool = ToolInfo(
                name="test_function",
                description="Test function",
                parameters={"input": "string"},
                return_type="string"
            )
            
            request = ServiceRegistrationRequest(
                name="Test Service",
                description="A test service",
                service_type=ServiceType.FUNCTION,
                hosting_mode=HostingMode.SSE,
                script_id="test-script",
                tools=[tool]
            )
            
            service_config = await registry.register_service(request)
            assert service_config.name == "Test Service"
            assert service_config.status == ServiceStatus.INACTIVE
            
            # Test service retrieval
            retrieved = registry.get_service(service_config.service_id)
            assert retrieved is not None
            assert retrieved.name == "Test Service"
            
            # Test service by name
            by_name = registry.get_service_by_name("Test Service")
            assert by_name is not None
            assert by_name.service_id == service_config.service_id
            
            # Test status update
            success = await registry.update_service_status(service_config.service_id, ServiceStatus.ACTIVE)
            assert success is True
            
            updated = registry.get_service(service_config.service_id)
            assert updated.status == ServiceStatus.ACTIVE
            
            # Test service listing
            services = registry.list_services()
            assert len(services) == 1
            
            active_services = registry.list_services(ServiceStatus.ACTIVE)
            assert len(active_services) == 1
            
            # Test statistics
            stats = registry.get_service_stats()
            assert stats["total_services"] == 1
            assert stats["active_services"] == 1
            
            # Test service unregistration
            success = await registry.unregister_service(service_config.service_id)
            assert success is True
            
            services = registry.list_services()
            assert len(services) == 0
            
        print("✅ Service registry working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Service registry test failed: {e}")
        return False


async def test_health_monitor():
    """Test health monitoring functionality."""
    print("\n🏥 Testing health monitor...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            services_dir = Path(temp_dir) / "services"
            wrappers_dir = Path(temp_dir) / "wrappers"
            services_dir.mkdir()
            wrappers_dir.mkdir()
            
            registry = ServiceRegistry(services_dir)
            health_monitor = HealthMonitor(registry, wrappers_dir)
            
            # Register a test service
            tool = ToolInfo(
                name="test_function",
                description="Test function",
                parameters={},
                return_type="string"
            )
            
            request = ServiceRegistrationRequest(
                name="Test Service",
                description="A test service",
                service_type=ServiceType.FUNCTION,
                hosting_mode=HostingMode.SSE,
                script_id="test-script",
                tools=[tool]
            )
            
            service_config = await registry.register_service(request)
            
            # Test health check (will fail since no actual wrapper exists)
            health_result = await health_monitor.check_service_health(service_config.service_id)
            assert health_result.service_id == service_config.service_id
            assert health_result.status == ServiceStatus.ERROR
            assert "not found" in health_result.error_message.lower()
            
            # Test health result retrieval
            stored_result = health_monitor.get_health_result(service_config.service_id)
            assert stored_result is not None
            assert stored_result.service_id == service_config.service_id
            
        print("✅ Health monitor working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Health monitor test failed: {e}")
        return False


async def test_service_manager():
    """Test service manager functionality."""
    print("\n🎯 Testing service manager...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            services_dir = Path(temp_dir) / "services"
            wrappers_dir = Path(temp_dir) / "wrappers"
            services_dir.mkdir()
            wrappers_dir.mkdir()
            
            route_manager = RouteManager()
            service_manager = ServiceManager(services_dir, wrappers_dir, route_manager)
            
            await service_manager.start()
            
            try:
                # Test service registration
                tool = ToolInfo(
                    name="test_function",
                    description="Test function",
                    parameters={},
                    return_type="string"
                )
                
                request = ServiceRegistrationRequest(
                    name="Test Service",
                    description="A test service",
                    service_type=ServiceType.FUNCTION,
                    hosting_mode=HostingMode.SSE,
                    script_id="test-script",
                    tools=[tool]
                )
                
                service_config = await service_manager.register_service(request)
                assert service_config.name == "Test Service"
                
                # Test service retrieval
                retrieved = service_manager.get_service(service_config.service_id)
                assert retrieved is not None
                
                # Test service listing
                services = service_manager.list_services()
                assert len(services) == 1
                
                # Test statistics
                stats = service_manager.get_service_stats()
                assert "registry" in stats
                assert "health_checks" in stats
                
            finally:
                await service_manager.stop()
            
        print("✅ Service manager working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Service manager test failed: {e}")
        return False


async def run_async_tests():
    """Run async tests."""
    results = []
    
    results.append(await test_service_registry())
    results.append(await test_health_monitor())
    results.append(await test_service_manager())
    
    return results


def main():
    """Run all Stage 6 service registry tests."""
    print("🚀 Stage 6 Service Registry Implementation Tests")
    print("=" * 50)
    
    # Run sync tests
    sync_results = [
        test_service_registry_models()
    ]
    
    # Run async tests
    async_results = asyncio.run(run_async_tests())
    
    # Combine results
    results = sync_results + async_results
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Stage 6 service registry tests passed!")
        print("\n✨ Stage 6 core functionality is working!")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    main()
