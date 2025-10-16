"""
Integration example for Roulette games (main_speed.py and main_vip.py).

This example shows how to integrate the time monitoring system into
existing Roulette game modules without interfering with their operation.
"""

import asyncio
from pathlib import Path
import sys

# Add the parent directory to the path to import the monitor
sys.path.append(str(Path(__file__).parent.parent))

from studio_roundtime_monitor import TimeMonitor
from studio_roundtime_monitor.utils.config import MonitorConfig
from studio_roundtime_monitor.core.event_system import EventType

class RouletteTimeMonitorIntegration:
    """
    Integration helper for Roulette games.

    This class provides methods to integrate time monitoring into
    existing Roulette game modules.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the integration.

        Args:
            config_path: Path to monitor configuration file
        """
        self.config_path = config_path or "config/monitor_config.yaml"
        self.time_monitor = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the time monitor."""
        if self._initialized:
            return

        try:
            # Load configuration
            config = MonitorConfig()
            if Path(self.config_path).exists():
                from studio_roundtime_monitor.utils.config import load_config
                config = load_config(self.config_path)

            # Initialize time monitor
            self.time_monitor = TimeMonitor(config)
            await self.time_monitor.start()

            self._initialized = True
            print("✅ Time monitor initialized successfully")

        except Exception as e:
            print(f"❌ Failed to initialize time monitor: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup the time monitor."""
        if self.time_monitor:
            await self.time_monitor.stop()
            self._initialized = False
            print("✅ Time monitor cleaned up")

    # TableAPI integration methods

    def record_tableapi_start(self, table: str, round_id: str) -> None:
        """Record TableAPI start event."""
        if not self._initialized:
            return

        self.time_monitor.publish_event(
            event_type=EventType.TABLEAPI_START,
            game_type="roulette",
            table=table,
            round_id=round_id
        )
        print(f"📊 Recorded TableAPI start: {table} - {round_id}")

    def record_tableapi_betstop(self, table: str, round_id: str) -> None:
        """Record TableAPI betstop event."""
        if not self._initialized:
            return

        self.time_monitor.publish_event(
            event_type=EventType.TABLEAPI_BETSTOP,
            game_type="roulette",
            table=table,
            round_id=round_id
        )
        print(f"📊 Recorded TableAPI betstop: {table} - {round_id}")

    def record_tableapi_deal(self, table: str, round_id: str, winning_number: int = None) -> None:
        """Record TableAPI deal event."""
        if not self._initialized:
            return

        data = {}
        if winning_number is not None:
            data["winning_number"] = winning_number

        self.time_monitor.publish_event(
            event_type=EventType.TABLEAPI_DEAL,
            game_type="roulette",
            table=table,
            round_id=round_id,
            **data
        )
        print(f"📊 Recorded TableAPI deal: {table} - {round_id} - {winning_number}")

    def record_tableapi_finish(self, table: str, round_id: str) -> None:
        """Record TableAPI finish event."""
        if not self._initialized:
            return

        self.time_monitor.publish_event(
            event_type=EventType.TABLEAPI_FINISH,
            game_type="roulette",
            table=table,
            round_id=round_id
        )
        print(f"📊 Recorded TableAPI finish: {table} - {round_id}")

    # Roulette device integration methods

    def record_roulette_x2(self, table: str, round_id: str, warning_flag: str = None) -> None:
        """Record *X;2 event (ball launch)."""
        if not self._initialized:
            return

        data = {}
        if warning_flag is not None:
            data["warning_flag"] = warning_flag

        self.time_monitor.publish_event(
            event_type=EventType.ROULETTE_X2,
            game_type="roulette",
            table=table,
            round_id=round_id,
            **data
        )
        print(f"🎯 Recorded *X;2: {table} - {round_id} - warning_flag={warning_flag}")

    def record_roulette_x3(self, table: str, round_id: str) -> None:
        """Record *X;3 event (ball landing)."""
        if not self._initialized:
            return

        self.time_monitor.publish_event(
            event_type=EventType.ROULETTE_X3,
            game_type="roulette",
            table=table,
            round_id=round_id
        )
        print(f"🎯 Recorded *X;3: {table} - {round_id}")

    def record_roulette_x4(self, table: str, round_id: str) -> None:
        """Record *X;4 event (detection)."""
        if not self._initialized:
            return

        self.time_monitor.publish_event(
            event_type=EventType.ROULETTE_X4,
            game_type="roulette",
            table=table,
            round_id=round_id
        )
        print(f"🎯 Recorded *X;4: {table} - {round_id}")

    def record_roulette_x5(self, table: str, round_id: str, winning_number: int = None) -> None:
        """Record *X;5 event (result announcement)."""
        if not self._initialized:
            return

        data = {}
        if winning_number is not None:
            data["winning_number"] = winning_number

        self.time_monitor.publish_event(
            event_type=EventType.ROULETTE_X5,
            game_type="roulette",
            table=table,
            round_id=round_id,
            **data
        )
        print(f"🎯 Recorded *X;5: {table} - {round_id} - winning_number={winning_number}")

# Integration functions for existing code

def integrate_with_main_speed():
    """
    Example integration with main_speed.py.

    Add these calls to the appropriate places in your main_speed.py:
    """

    integration_code = '''
# Add this import at the top of main_speed.py
from studio_roundtime_monitor.examples.roulette_integration import RouletteTimeMonitorIntegration

# Initialize the integration (add this in main() function)
time_monitor = RouletteTimeMonitorIntegration()
asyncio.run(time_monitor.initialize())

# Add these calls in the appropriate places:

# In execute_start_post function, after successful start_post:
time_monitor.record_tableapi_start(table["name"], round_id)

# In execute_deal_post function, after successful deal_post:
time_monitor.record_tableapi_deal(table["name"], round_id, win_num)

# In execute_finish_post function, after successful finish_post:
time_monitor.record_tableapi_finish(table["name"], round_id)

# In read_from_serial function:

# When handling *X;2 messages:
if "*X;2" in data:
    # ... existing code ...
    time_monitor.record_roulette_x2(table["name"], round_id, warning_flag)

# When handling *X;3 messages:
elif "*X;3" in data and not isLaunch:
    # ... existing code ...
    time_monitor.record_roulette_x3(table["name"], round_id)

# When handling *X;5 messages:
elif "*X;5" in data and not deal_post_sent:
    # ... existing code ...
    time_monitor.record_roulette_x5(table["name"], round_id, win_num)

# Add cleanup in finally block:
try:
    # ... existing code ...
finally:
    asyncio.run(time_monitor.cleanup())
'''

    print("Integration code for main_speed.py:")
    print(integration_code)

def integrate_with_main_vip():
    """
    Example integration with main_vip.py.

    Similar to main_speed.py but with VIP-specific adjustments.
    """

    integration_code = '''
# Add this import at the top of main_vip.py
from studio_roundtime_monitor.examples.roulette_integration import RouletteTimeMonitorIntegration

# Initialize the integration (add this in main() function)
time_monitor = RouletteTimeMonitorIntegration()
asyncio.run(time_monitor.initialize())

# Add the same integration calls as in main_speed.py
# The integration is identical for both Speed and VIP Roulette
'''

    print("Integration code for main_vip.py:")
    print(integration_code)

async def demo_integration():
    """Demonstrate the integration functionality."""
    print("🚀 Starting Roulette Time Monitor Integration Demo")

    # Initialize integration
    monitor = RouletteTimeMonitorIntegration()
    await monitor.initialize()

    try:
        # Simulate a complete round
        table = "PRD"
        round_id = "DEMO123"
        winning_number = 7

        print(f"\n📋 Simulating round: {table} - {round_id}")

        # Simulate TableAPI events
        monitor.record_tableapi_start(table, round_id)
        await asyncio.sleep(0.1)

        monitor.record_tableapi_betstop(table, round_id)
        await asyncio.sleep(0.1)

        monitor.record_tableapi_deal(table, round_id, winning_number)
        await asyncio.sleep(0.1)

        monitor.record_tableapi_finish(table, round_id)
        await asyncio.sleep(0.1)

        # Simulate Roulette device events
        monitor.record_roulette_x2(table, round_id, "0")
        await asyncio.sleep(0.1)

        monitor.record_roulette_x3(table, round_id)
        await asyncio.sleep(0.1)

        monitor.record_roulette_x4(table, round_id)
        await asyncio.sleep(0.1)

        monitor.record_roulette_x5(table, round_id, winning_number)

        # Wait for processing
        await asyncio.sleep(2.0)

        # Get statistics
        stats = monitor.time_monitor.get_statistics()
        print(f"\n📊 Statistics: {stats}")

    finally:
        await monitor.cleanup()

    print("✅ Demo completed")

if __name__ == "__main__":
    print("Roulette Time Monitor Integration Examples")
    print("=" * 50)

    print("\n1. Integration with main_speed.py:")
    integrate_with_main_speed()

    print("\n2. Integration with main_vip.py:")
    integrate_with_main_vip()

    print("\n3. Running demo...")
    asyncio.run(demo_integration())
