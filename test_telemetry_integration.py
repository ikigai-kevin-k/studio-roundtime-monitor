#!/usr/bin/env python3
"""
Test script for Studio Round Time Monitor telemetry integration.

This script tests the integration with remote Loki and Prometheus servers
deployed on GE or TPE telemetry infrastructure.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from studio_roundtime_monitor.core.time_monitor import TimeMonitor
from studio_roundtime_monitor.utils.config import load_config
from studio_roundtime_monitor.core.interval_calculator import IntervalType
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def test_telemetry_integration():
    """Test telemetry integration with remote servers."""
    print("🚀 Testing Studio Round Time Monitor Telemetry Integration")
    print("=" * 60)
    
    # Load configuration
    config_path = "config/telemetry_config.yaml"
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure the telemetry configuration file exists.")
        return False
    
    try:
        config = load_config(config_path)
        print(f"✅ Configuration loaded from: {config_path}")
        print(f"📊 Storage type: {config.storage.type}")
        
        if config.storage.type != "telemetry":
            print("❌ Configuration is not set to use telemetry storage")
            return False
        
        # Initialize time monitor
        monitor = TimeMonitor(config)
        print("✅ Time monitor initialized")
        
        # Test telemetry connections
        print("\n🔗 Testing telemetry connections...")
        connection_results = await monitor.test_telemetry_connections()
        
        for service, result in connection_results.items():
            status = "✅" if result else "❌"
            print(f"  {status} {service}: {'Connected' if result else 'Failed'}")
        
        # Check if any service is connected
        if not any(connection_results.values()):
            print("❌ No telemetry services are connected")
            return False
        
        # Start the monitor
        print("\n🔄 Starting time monitor...")
        await monitor.start()
        print("✅ Time monitor started")
        
        # Simulate some monitoring events
        print("\n📝 Simulating monitoring events...")
        
        # Simulate TableAPI events
        print("  📊 Simulating TableAPI events...")
        monitor.record_tableapi_event("start", "roulette", "PRD", "test_round_001")
        await asyncio.sleep(0.1)
        monitor.record_tableapi_event("betstop", "roulette", "PRD", "test_round_001")
        await asyncio.sleep(0.1)
        monitor.record_tableapi_event("deal", "roulette", "PRD", "test_round_001")
        await asyncio.sleep(0.1)
        monitor.record_tableapi_event("finish", "roulette", "PRD", "test_round_001")
        
        # Simulate Roulette events
        print("  🎰 Simulating Roulette events...")
        monitor.record_roulette_event("*X;2", "roulette", "PRD", "test_round_002")
        await asyncio.sleep(0.1)
        monitor.record_roulette_event("*X;3", "roulette", "PRD", "test_round_002")
        await asyncio.sleep(0.1)
        monitor.record_roulette_event("*X;4", "roulette", "PRD", "test_round_002")
        await asyncio.sleep(0.1)
        monitor.record_roulette_event("*X;5", "roulette", "PRD", "test_round_002")
        
        # Simulate Sicbo events
        print("  🎲 Simulating Sicbo events...")
        monitor.record_sicbo_event("shakerStart", "sicbo", "SBO", "test_round_003")
        await asyncio.sleep(0.1)
        monitor.record_sicbo_event("shakerStop", "sicbo", "SBO", "test_round_003")
        await asyncio.sleep(0.1)
        monitor.record_sicbo_event("idpSend", "sicbo", "SBO", "test_round_003")
        await asyncio.sleep(0.1)
        monitor.record_sicbo_event("idpReceive", "sicbo", "SBO", "test_round_003")
        
        # Wait for data to be processed and sent
        print("\n⏳ Waiting for data to be processed and sent to telemetry servers...")
        await asyncio.sleep(10)  # Wait for processing cycle
        
        # Get statistics
        print("\n📈 Getting monitoring statistics...")
        stats = monitor.get_statistics()
        for interval_type, data in stats.items():
            print(f"  📊 {interval_type}: {data['count']} intervals, avg: {data['avg_duration']:.3f}s")
        
        # Get health status
        print("\n🏥 Getting health status...")
        health = monitor.get_health_status()
        print(f"  🔄 Running: {health['running']}")
        print(f"  📡 Event subscribers: {sum(health['event_system_subscribers'].values())}")
        print(f"  🎯 Monitors: {health['monitors']}")
        
        # Stop the monitor
        print("\n🛑 Stopping time monitor...")
        await monitor.stop()
        print("✅ Time monitor stopped")
        
        print("\n🎉 Telemetry integration test completed successfully!")
        print("\n📋 Next steps:")
        print("  1. Check Loki logs at: http://100.64.0.113:3100")
        print("  2. Check Prometheus metrics at: http://100.64.0.113:9090")
        print("  3. View Grafana dashboards at: http://100.64.0.113:3000")
        print("  4. Query logs: {job=\"studio-roundtime-monitor\"}")
        print("  5. Query metrics: time_interval_duration")
        
        return True
        
    except Exception as e:
        logger.error("Test failed", error=str(e))
        print(f"❌ Test failed: {e}")
        return False


async def test_telemetry_clients_directly():
    """Test telemetry clients directly without the full monitor."""
    print("\n🔧 Testing telemetry clients directly...")
    
    try:
        from studio_roundtime_monitor.telemetry.loki_client import LokiClient
        from studio_roundtime_monitor.telemetry.prometheus_client import PrometheusClient
        
        # Test Loki client
        print("  📝 Testing Loki client...")
        loki_client = LokiClient("http://100.64.0.113:3100", "test-instance")
        loki_result = loki_client.test_connection()
        print(f"    {'✅' if loki_result else '❌'} Loki: {'Connected' if loki_result else 'Failed'}")
        
        # Test Prometheus client
        print("  📊 Testing Prometheus client...")
        prometheus_client = PrometheusClient("http://100.64.0.113:9091", "test-job")
        prometheus_result = prometheus_client.test_connection()
        print(f"    {'✅' if prometheus_result else '❌'} Prometheus: {'Connected' if prometheus_result else 'Failed'}")
        
        return loki_result and prometheus_result
        
    except Exception as e:
        print(f"❌ Direct client test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("Studio Round Time Monitor - Telemetry Integration Test")
    print("=" * 60)
    
    # Test direct client connections first
    direct_test_passed = await test_telemetry_clients_directly()
    
    if not direct_test_passed:
        print("\n❌ Direct client tests failed. Please check:")
        print("  1. Telemetry servers are running")
        print("  2. Network connectivity to servers")
        print("  3. Server URLs are correct")
        return
    
    # Test full integration
    integration_test_passed = await test_telemetry_integration()
    
    if integration_test_passed:
        print("\n🎉 All tests passed! Telemetry integration is working correctly.")
    else:
        print("\n❌ Integration test failed. Please check the configuration and logs.")


if __name__ == "__main__":
    asyncio.run(main())
