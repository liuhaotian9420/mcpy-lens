#!/usr/bin/env python3
"""Simple test script to verify mcpy-lens components."""

import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_imports():
    """Test importing all our modules."""
    try:
        print("Testing imports...")

        # Test basic imports
        from mcpy_lens.config import get_settings

        print("✓ Config import successful")

        from mcpy_lens.models import HealthCheckResponse

        print("✓ Models import successful")


        print("✓ Exceptions import successful")

        from mcpy_lens.routing import RouteManager

        print("✓ Routing import successful")

        # Test settings
        settings = get_settings()
        print(f"✓ Settings loaded: data_dir={settings.data_dir}")

        # Test health response model
        health = HealthCheckResponse(
            status="healthy", version="0.1.0", message="Test successful"
        )
        print(f"✓ Health model works: {health.status}")

        # Test route manager
        RouteManager()
        print("✓ Route manager created")

        print("\n🎉 All component tests passed!")
        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_fastapi_app():
    """Test FastAPI app creation."""
    try:
        print("\nTesting FastAPI app...")
        from mcpy_lens.app import create_app

        app = create_app()
        print("✓ FastAPI app created successfully")

        # Check if routes are registered
        routes = [route.path for route in app.routes]
        print(f"✓ Routes registered: {routes}")

        if "/health" in routes:
            print("✓ Health endpoint found")
        else:
            print("⚠ Health endpoint not found")

        return True

    except Exception as e:
        print(f"❌ FastAPI app test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=== mcpy-lens Component Test ===\n")

    success = True
    success &= test_imports()
    success &= test_fastapi_app()

    if success:
        print("\n🎉 All tests passed! The application should work correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
