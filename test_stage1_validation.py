#!/usr/bin/env python3
"""
Stage 1 Validation Tests
Test script to validate remaining Stage 1 acceptance criteria.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict

import httpx
from fastapi.testclient import TestClient

from mcpy_lens.app import create_app


class Stage1Validator:
    """Validator for Stage 1 acceptance criteria."""

    def __init__(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.server_process = None
        self.server_thread = None
        self.base_url = "http://127.0.0.1:8000"

    def setup_test_server(self) -> None:
        """Start a test server in a separate thread."""
        def run_server():
            uvicorn.run(
                self.app,
                host="127.0.0.1",
                port=8000,
                log_level="warning"
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        # Verify server is running
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                raise RuntimeError("Server failed to start properly")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to test server: {e}")

    def test_health_check_endpoint(self) -> Dict[str, Any]:
        """Test health check endpoint returns 200 status."""
        print("🔍 Testing health check endpoint...")
        
        try:
            # Test with TestClient (synchronous)
            response = self.client.get("/health")
            
            result = {
                "test_name": "Health Check Endpoint",
                "status": "PASS" if response.status_code == 200 else "FAIL",
                "status_code": response.status_code,
                "response_data": response.json() if response.status_code == 200 else None,
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["status", "version", "message"]
                missing_fields = [field for field in expected_fields if field not in data]
                
                if missing_fields:
                    result["status"] = "FAIL"
                    result["error"] = f"Missing fields in response: {missing_fields}"
                elif data.get("status") != "healthy":
                    result["status"] = "FAIL"
                    result["error"] = f"Expected status 'healthy', got '{data.get('status')}'"
            else:
                result["error"] = f"Expected status 200, got {response.status_code}"
                
        except Exception as e:
            result = {
                "test_name": "Health Check Endpoint",
                "status": "FAIL",
                "error": str(e)
            }
        
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result['test_name']}: {result['status']}")
        if result.get("error"):
            print(f"      Error: {result['error']}")
            
        return result

    def test_dynamic_route_operations(self) -> Dict[str, Any]:
        """Test dynamic route addition/removal works without server restart."""
        print("🔍 Testing dynamic route operations...")
        
        try:
            # Access the route manager from the app state
            route_manager = self.app.state.route_manager
            
            # Test adding a dynamic route
            test_route_added = False
            test_route_removed = False
            route_conflicts_detected = False
            
            # Create a simple test endpoint
            async def test_endpoint():
                return {"message": "dynamic route test"}
            
            # Test route addition
            try:
                route_manager.add_route(
                    path="/test-dynamic",
                    endpoint=test_endpoint,
                    methods=["GET"],
                    service_id="test-service-1"
                )
                test_route_added = True
            except Exception as e:
                return {
                    "test_name": "Dynamic Route Operations",
                    "status": "FAIL",
                    "error": f"Failed to add route: {e}"
                }
            
            # Test route conflict detection
            try:
                route_manager.add_route(
                    path="/test-dynamic",
                    endpoint=test_endpoint,
                    methods=["GET"],
                    service_id="test-service-2"
                )
                # If no exception, conflict detection failed
                route_conflicts_detected = False
            except Exception:
                # Exception expected for conflict
                route_conflicts_detected = True
            
            # Test route removal
            try:
                route_manager.remove_service_routes("test-service-1")
                test_route_removed = True
            except Exception as e:
                return {
                    "test_name": "Dynamic Route Operations",
                    "status": "FAIL",
                    "error": f"Failed to remove route: {e}"
                }
            
            # Check if all operations succeeded
            all_passed = test_route_added and test_route_removed and route_conflicts_detected
            
            result = {
                "test_name": "Dynamic Route Operations",
                "status": "PASS" if all_passed else "FAIL",
                "details": {
                    "route_addition": "PASS" if test_route_added else "FAIL",
                    "route_removal": "PASS" if test_route_removed else "FAIL",
                    "conflict_detection": "PASS" if route_conflicts_detected else "FAIL"
                },
                "error": None if all_passed else "Some dynamic route operations failed"
            }
            
        except Exception as e:
            result = {
                "test_name": "Dynamic Route Operations",
                "status": "FAIL",
                "error": str(e)
            }
        
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result['test_name']}: {result['status']}")
        if result.get("error"):
            print(f"      Error: {result['error']}")
        if result.get("details"):
            for operation, status in result["details"].items():
                print(f"      {operation}: {'✅' if status == 'PASS' else '❌'}")
            
        return result

    def test_thread_safety_concurrent_access(self) -> Dict[str, Any]:
        """Test thread-safe operations under concurrent access."""
        print("🔍 Testing thread safety under concurrent access...")
        
        try:
            route_manager = self.app.state.route_manager
            
            # Test concurrent route operations
            def add_test_route(service_id: str, route_num: int):
                try:
                    async def test_endpoint():
                        return {"service": service_id, "route": route_num}
                    
                    route_manager.add_route(
                        path=f"/test-concurrent-{service_id}-{route_num}",
                        endpoint=test_endpoint,
                        methods=["GET"],
                        service_id=f"{service_id}-{route_num}"
                    )
                    return True
                except Exception as e:
                    print(f"Error adding route {service_id}-{route_num}: {e}")
                    return False
            
            def remove_test_route(service_id: str, route_num: int):
                try:
                    route_manager.remove_service_routes(f"{service_id}-{route_num}")
                    return True
                except Exception as e:
                    print(f"Error removing route {service_id}-{route_num}: {e}")
                    return False
            
            # Run concurrent operations
            successful_operations = 0
            total_operations = 20
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit concurrent route addition tasks
                add_futures = [
                    executor.submit(add_test_route, "concurrent-test", i)
                    for i in range(total_operations // 2)
                ]
                
                # Wait for additions to complete
                for future in as_completed(add_futures):
                    if future.result():
                        successful_operations += 1
                
                # Submit concurrent route removal tasks
                remove_futures = [
                    executor.submit(remove_test_route, "concurrent-test", i)
                    for i in range(total_operations // 2)
                ]
                
                # Wait for removals to complete
                for future in as_completed(remove_futures):
                    if future.result():
                        successful_operations += 1
            
            # Check success rate
            success_rate = successful_operations / total_operations
            thread_safety_passed = success_rate >= 0.9  # 90% success rate threshold
            
            result = {
                "test_name": "Thread Safety Concurrent Access",
                "status": "PASS" if thread_safety_passed else "FAIL",
                "details": {
                    "successful_operations": successful_operations,
                    "total_operations": total_operations,
                    "success_rate": f"{success_rate:.2%}"
                },
                "error": None if thread_safety_passed else f"Success rate {success_rate:.2%} below 90% threshold"
            }
            
        except Exception as e:
            result = {
                "test_name": "Thread Safety Concurrent Access",
                "status": "FAIL",
                "error": str(e)
            }
        
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result['test_name']}: {result['status']}")
        if result.get("error"):
            print(f"      Error: {result['error']}")
        if result.get("details"):
            for key, value in result["details"].items():
                print(f"      {key}: {value}")
            
        return result

    def run_all_validations(self) -> Dict[str, Any]:
        """Run all Stage 1 validation tests."""
        print("🚀 Starting Stage 1 Validation Tests")
        print("=" * 50)
        
        results = []
        
        # Test 1: Health check endpoint
        results.append(self.test_health_check_endpoint())
        
        # Test 2: Dynamic route operations
        results.append(self.test_dynamic_route_operations())
        
        # Test 3: Thread safety under concurrent access
        results.append(self.test_thread_safety_concurrent_access())
        
        # Summary
        passed_tests = sum(1 for result in results if result["status"] == "PASS")
        total_tests = len(results)
        
        print("\n" + "=" * 50)
        print("🏁 Stage 1 Validation Summary")
        print(f"Tests passed: {passed_tests}/{total_tests}")
        
        overall_status = "PASS" if passed_tests == total_tests else "FAIL"
        print(f"Overall Status: {'✅ PASS' if overall_status == 'PASS' else '❌ FAIL'}")
        
        if overall_status == "PASS":
            print("\n🎉 Stage 1: Core Infrastructure Setup - COMPLETE!")
            print("Ready to proceed to Stage 2: File Upload Management")
        else:
            print("\n⚠️  Some tests failed. Please review and fix issues before proceeding.")
        
        return {
            "overall_status": overall_status,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "test_results": results
        }


def main():
    """Main entry point for validation tests."""
    # Setup logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    # Create validator and run tests
    validator = Stage1Validator()
    
    try:
        results = validator.run_all_validations()
        
        # Exit with appropriate code
        exit_code = 0 if results["overall_status"] == "PASS" else 1
        exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Validation failed with error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
