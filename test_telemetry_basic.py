#!/usr/bin/env python3
"""
Simple test script for telemetry integration.

This script tests basic telemetry functionality without the full monitor.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all telemetry modules can be imported."""
    try:
        from studio_roundtime_monitor.telemetry.loki_client import LokiClient
        from studio_roundtime_monitor.telemetry.prometheus_client import PrometheusClient
        from studio_roundtime_monitor.telemetry.telemetry_storage import TelemetryStorage
        from studio_roundtime_monitor.storage.telemetry_storage import TelemetryStorageBackend
        print("✅ All telemetry modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_client_creation():
    """Test creating telemetry clients."""
    try:
        from studio_roundtime_monitor.telemetry.loki_client import LokiClient
        from studio_roundtime_monitor.telemetry.prometheus_client import PrometheusClient
        
        # Test Loki client creation
        loki_client = LokiClient("http://localhost:3100", "test-instance")
        print("✅ Loki client created successfully")
        
        # Test Prometheus client creation
        prometheus_client = PrometheusClient("http://localhost:9091", "test-job")
        print("✅ Prometheus client created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Client creation error: {e}")
        return False

def test_storage_backend():
    """Test creating telemetry storage backend."""
    try:
        from studio_roundtime_monitor.storage.telemetry_storage import TelemetryStorageBackend
        
        # Test storage backend creation
        storage = TelemetryStorageBackend(
            loki_url="http://localhost:3100",
            prometheus_url="http://localhost:9091"
        )
        print("✅ Telemetry storage backend created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Storage backend creation error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Studio Round Time Monitor Telemetry Integration")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Client Creation Tests", test_client_creation),
        ("Storage Backend Tests", test_storage_backend),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Telemetry integration is ready.")
        print("\n📋 Next steps:")
        print("  1. Configure telemetry servers in config/telemetry_config.yaml")
        print("  2. Run: python test_telemetry_integration.py")
        print("  3. Start monitoring with telemetry integration")
    else:
        print("❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
