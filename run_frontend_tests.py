#!/usr/bin/env python3
"""Frontend test runner for mcpy-lens Gradio interface."""

import sys
import subprocess
import time
import requests
import argparse
from pathlib import Path
from typing import Optional


def check_server(url: str, timeout: int = 5) -> bool:
    """Check if a server is running at the given URL."""
    try:
        response = requests.get(f"{url}/", timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def wait_for_server(url: str, max_wait: int = 30) -> bool:
    """Wait for a server to become available."""
    print(f"Waiting for server at {url}...")
    for i in range(max_wait):
        if check_server(url):
            print(f"✅ Server at {url} is ready")
            return True
        time.sleep(1)
        if i % 5 == 0:
            print(f"Still waiting... ({i}/{max_wait})")
    
    print(f"❌ Server at {url} did not become available within {max_wait} seconds")
    return False


def start_backend_server() -> Optional[subprocess.Popen]:
    """Start the FastAPI backend server."""
    try:
        print("🚀 Starting FastAPI backend server...")
        process = subprocess.Popen(
            [sys.executable, "run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to start
        if wait_for_server("http://localhost:8090", max_wait=30):
            return process
        else:
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Failed to start backend server: {e}")
        return None


def start_frontend_server() -> Optional[subprocess.Popen]:
    """Start the Gradio frontend server."""
    try:
        print("🚀 Starting Gradio frontend server...")
        process = subprocess.Popen(
            [sys.executable, "launch_gradio.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to start
        if wait_for_server("http://localhost:7860", max_wait=30):
            return process
        else:
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Failed to start frontend server: {e}")
        return None


def install_playwright_browsers():
    """Install Playwright browsers if needed."""
    try:
        print("🔧 Installing Playwright browsers...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            print("✅ Playwright browsers installed successfully")
            return True
        else:
            print(f"❌ Failed to install Playwright browsers: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Playwright browser installation timed out")
        return False
    except Exception as e:
        print(f"❌ Error installing Playwright browsers: {e}")
        return False


def run_tests(test_pattern: str = "tests/frontend/", headless: bool = True, 
              browser: str = "chromium", slow_mo: int = 0) -> bool:
    """Run the frontend tests."""
    try:
        print(f"🧪 Running frontend tests: {test_pattern}")
        
        # Set environment variables for Playwright
        env = {
            "PLAYWRIGHT_HEADLESS": "true" if headless else "false",
            "PLAYWRIGHT_SLOW_MO": str(slow_mo),
        }
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            test_pattern,
            "-v",
            "--tb=short",
            f"--browser={browser}",
            "-m", "frontend"
        ]
        
        if not headless:
            cmd.append("--headed")
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Run tests
        result = subprocess.run(
            cmd,
            env={**subprocess.os.environ, **env},
            timeout=600  # 10 minutes timeout
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run frontend tests for mcpy-lens")
    parser.add_argument("--no-headless", action="store_true", 
                       help="Run tests in headed mode (visible browser)")
    parser.add_argument("--browser", default="chromium", 
                       choices=["chromium", "firefox", "webkit"],
                       help="Browser to use for testing")
    parser.add_argument("--slow-mo", type=int, default=0,
                       help="Slow down operations by specified milliseconds")
    parser.add_argument("--test-pattern", default="tests/frontend/",
                       help="Test pattern to run")
    parser.add_argument("--skip-install", action="store_true",
                       help="Skip Playwright browser installation")
    parser.add_argument("--manual-servers", action="store_true",
                       help="Assume servers are already running manually")
    
    args = parser.parse_args()
    
    print("🎭 mcpy-lens Frontend Test Runner")
    print("=" * 50)
    
    # Install Playwright browsers if needed
    if not args.skip_install:
        if not install_playwright_browsers():
            print("❌ Failed to install Playwright browsers")
            return 1
    
    backend_process = None
    frontend_process = None
    
    try:
        if not args.manual_servers:
            # Check if servers are already running
            backend_running = check_server("http://localhost:8090")
            frontend_running = check_server("http://localhost:7860")
            
            if backend_running and frontend_running:
                print("✅ Both servers are already running")
            else:
                # Start backend server
                if not backend_running:
                    backend_process = start_backend_server()
                    if not backend_process:
                        print("❌ Failed to start backend server")
                        return 1
                
                # Start frontend server
                if not frontend_running:
                    frontend_process = start_frontend_server()
                    if not frontend_process:
                        print("❌ Failed to start frontend server")
                        return 1
        else:
            print("🔧 Manual server mode - assuming servers are running")
            if not (check_server("http://localhost:8090") and check_server("http://localhost:7860")):
                print("❌ Servers not detected. Please start them manually:")
                print("  Backend: python run.py")
                print("  Frontend: python launch_gradio.py")
                return 1
        
        # Run the tests
        success = run_tests(
            test_pattern=args.test_pattern,
            headless=not args.no_headless,
            browser=args.browser,
            slow_mo=args.slow_mo
        )
        
        if success:
            print("\n🎉 All frontend tests passed!")
            return 0
        else:
            print("\n❌ Some frontend tests failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
        
    finally:
        # Clean up servers
        if backend_process:
            print("🛑 Stopping backend server...")
            backend_process.terminate()
            backend_process.wait(timeout=10)
            
        if frontend_process:
            print("🛑 Stopping frontend server...")
            frontend_process.terminate()
            frontend_process.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
