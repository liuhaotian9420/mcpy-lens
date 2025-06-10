#!/usr/bin/env python3
"""Test frontend setup without Playwright - basic connectivity tests."""

import sys
import time
import requests
import subprocess
from pathlib import Path


def check_server(url: str, timeout: int = 5) -> bool:
    """Check if a server is running at the given URL."""
    try:
        response = requests.get(f"{url}/", timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def test_api_server():
    """Test FastAPI server connectivity."""
    print("🔍 Testing FastAPI server...")
    
    if not check_server("http://localhost:8090"):
        print("❌ FastAPI server not running at http://localhost:8090")
        print("Please start it with: python run.py")
        return False
    
    try:
        response = requests.get("http://localhost:8090/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API server healthy: {data}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API health check error: {e}")
        return False


def test_gradio_server():
    """Test Gradio server connectivity."""
    print("🔍 Testing Gradio server...")
    
    if not check_server("http://localhost:7860"):
        print("❌ Gradio server not running at http://localhost:7860")
        print("Please start it with: python launch_gradio.py")
        return False
    
    try:
        response = requests.get("http://localhost:7860/", timeout=10)
        if response.status_code == 200:
            print("✅ Gradio server accessible")
            
            # Check if the response contains Gradio-specific content
            content = response.text.lower()
            if "gradio" in content or "mcpy-lens" in content:
                print("✅ Gradio interface detected")
                return True
            else:
                print("⚠️  Server responding but may not be Gradio interface")
                return True
        else:
            print(f"❌ Gradio server returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Gradio server error: {e}")
        return False


def test_api_endpoints():
    """Test key API endpoints."""
    print("🔍 Testing API endpoints...")
    
    base_url = "http://localhost:8090"
    endpoints = [
        "/health",
        "/files/",
        "/services/",
    ]
    
    results = {}
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            results[endpoint] = response.status_code
            if response.status_code == 200:
                print(f"✅ {endpoint}: OK")
            else:
                print(f"⚠️  {endpoint}: {response.status_code}")
        except Exception as e:
            results[endpoint] = f"Error: {e}"
            print(f"❌ {endpoint}: {e}")
    
    return all(isinstance(status, int) and status < 500 for status in results.values())


def test_file_upload_api():
    """Test file upload API endpoint."""
    print("🔍 Testing file upload API...")
    
    # Create a test Python file
    test_content = '''def hello():
    return "Hello from test file!"
'''
    
    try:
        # Test file upload
        files = {'file': ('test_upload.py', test_content, 'text/plain')}
        response = requests.post(
            "http://localhost:8090/files/upload",
            files=files,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ File upload API working")
            
            # Test file listing
            list_response = requests.get("http://localhost:8090/files/", timeout=5)
            if list_response.status_code == 200:
                files_data = list_response.json()
                print(f"✅ File listing API working: {len(files_data)} files")
                return True
            else:
                print(f"⚠️  File listing failed: {list_response.status_code}")
                return False
        else:
            print(f"❌ File upload failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ File upload test error: {e}")
        return False


def test_gradio_app_structure():
    """Test that Gradio app can be imported and created."""
    print("🔍 Testing Gradio app structure...")
    
    try:
        # Add src to path
        src_dir = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_dir))
        
        # Test imports
        from mcpy_lens.gradio_app.main import create_gradio_app
        from mcpy_lens.gradio_app.api_client import APIClient
        
        print("✅ Gradio app modules imported successfully")
        
        # Test app creation (without launching)
        app = create_gradio_app()
        print("✅ Gradio app created successfully")
        
        # Test API client
        client = APIClient()
        print("✅ API client created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Gradio app structure test failed: {e}")
        return False


def main():
    """Run all frontend setup tests."""
    print("🎭 Frontend Setup Test Suite")
    print("=" * 50)
    
    tests = [
        ("API Server", test_api_server),
        ("Gradio Server", test_gradio_server),
        ("API Endpoints", test_api_endpoints),
        ("File Upload API", test_file_upload_api),
        ("Gradio App Structure", test_gradio_app_structure),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Frontend setup is ready.")
        print("\nNext steps for Playwright testing:")
        print("1. Install Playwright: pip install playwright pytest-playwright")
        print("2. Install browsers: python -m playwright install")
        print("3. Run frontend tests: python run_frontend_tests.py")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the issues above.")
        
        if not results.get("API Server", False):
            print("\n🚀 To start the API server: python run.py")
        if not results.get("Gradio Server", False):
            print("🚀 To start the Gradio server: python launch_gradio.py")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
