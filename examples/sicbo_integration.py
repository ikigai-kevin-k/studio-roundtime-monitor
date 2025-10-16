"""
Integration example for Sicbo game (main_sicbo.py).

This example shows how to integrate the time monitoring system into
the existing Sicbo game module without interfering with its operation.
"""

import asyncio
from pathlib import Path
import sys

# Add the parent directory to the path to import the monitor
sys.path.append(str(Path(__file__).parent.parent))

from studio_roundtime_monitor import TimeMonitor
from studio_roundtime_monitor.utils.config import MonitorConfig
from studio_roundtime_monitor.core.event_system import EventType

class SicboTimeMonitorIntegration:
    """
    Integration helper for Sicbo games.

    This class provides methods to integrate time monitoring into
    the existing Sicbo game module.
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
            print("✅ Sicbo time monitor initialized successfully")

        except Exception as e:
            print(f"❌ Failed to initialize Sicbo time monitor: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup the time monitor."""
        if self.time_monitor:
            await self.time_monitor.stop()
            self._initialized = False
            print("✅ Sicbo time monitor cleaned up")

    # TableAPI integration methods (same as Roulette)

    def record_tableapi_start(self, table: str, round_id: str) -> None:
        """Record TableAPI start event."""
        if not self._initialized:
            return

        self.time_monitor.publish_event(
            event_type=EventType.TABLEAPI_START,
            game_type="sicbo",
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
            game_type="sicbo",
            table=table,
            round_id=round_id
        )
        print(f"📊 Recorded TableAPI betstop: {table} - {round_id}")

    def record_tableapi_deal(self, table: str, round_id: str, dice_result: list = None) -> None:
        """Record TableAPI deal event."""
        if not self._initialized:
            return

        data = {}
        if dice_result is not None:
            data["dice_result"] = dice_result

        self.time_monitor.publish_event(
            event_type=EventType.TABLEAPI_DEAL,
            game_type="sicbo",
            table=table,
            round_id=round_id,
            **data
        )
        print(f"📊 Recorded TableAPI deal: {table} - {round_id} - {dice_result}")

    def record_tableapi_finish(self, table: str, round_id: str) -> None:
        """Record TableAPI finish event."""
        if not self._initialized:
            return

        self.time_monitor.publish_event(
            event_type=EventType.TABLEAPI_FINISH,
            game_type="sicbo",
            table=table,
            round_id=round_id
        )
        print(f"📊 Recorded TableAPI finish: {table} - {round_id}")

    # Sicbo shaker integration methods

    def record_shaker_start(self, table: str, round_id: str, command: str = None) -> None:
        """Record shaker start event."""
        if not self._initialized:
            return

        data = {}
        if command is not None:
            data["command"] = command

        self.time_monitor.publish_event(
            event_type=EventType.SICBO_SHAKER_START,
            game_type="sicbo",
            table=table,
            round_id=round_id,
            **data
        )
        print(f"🎲 Recorded shaker start: {table} - {round_id}")

    def record_shaker_stop(self, table: str, round_id: str, state: str = None) -> None:
        """Record shaker stop event."""
        if not self._initialized:
            return

        data = {}
        if state is not None:
            data["state"] = state

        self.time_monitor.publish_event(
            event_type=EventType.SICBO_SHAKER_STOP,
            game_type="sicbo",
            table=table,
            round_id=round_id,
            **data
        )
        print(f"🎲 Recorded shaker stop: {table} - {round_id}")

    def record_shaker_s0(self, table: str, round_id: str) -> None:
        """Record shaker S0 state event."""
        if not self._initialized:
            return

        self.time_monitor.publish_event(
            event_type=EventType.SICBO_SHAKER_S0,
            game_type="sicbo",
            table=table,
            round_id=round_id
        )
        print(f"🎲 Recorded shaker S0: {table} - {round_id}")

    # Sicbo IDP integration methods

    def record_idp_send(self, table: str, round_id: str, command: str = None) -> None:
        """Record IDP send event."""
        if not self._initialized:
            return

        data = {}
        if command is not None:
            data["command"] = command

        self.time_monitor.publish_event(
            event_type=EventType.SICBO_IDP_SEND,
            game_type="sicbo",
            table=table,
            round_id=round_id,
            **data
        )
        print(f"📷 Recorded IDP send: {table} - {round_id}")

    def record_idp_receive(self, table: str, round_id: str, result: list = None) -> None:
        """Record IDP receive event."""
        if not self._initialized:
            return

        data = {}
        if result is not None:
            data["result"] = result

        self.time_monitor.publish_event(
            event_type=EventType.SICBO_IDP_RECEIVE,
            game_type="sicbo",
            table=table,
            round_id=round_id,
            **data
        )
        print(f"📷 Recorded IDP receive: {table} - {round_id} - {result}")

def integrate_with_main_sicbo():
    """
    Example integration with main_sicbo.py.

    Add these calls to the appropriate places in your main_sicbo.py:
    """

    integration_code = '''
# Add this import at the top of main_sicbo.py
from studio_roundtime_monitor.examples.sicbo_integration import SicboTimeMonitorIntegration

# In SDPGame.__init__ method, add:
self.time_monitor = SicboTimeMonitorIntegration()

# In SDPGame.initialize method, after other initializations:
await self.time_monitor.initialize()

# In SDPGame.run_sicbo_game method:

# After successful start_post calls:
for table, round_id, bet_period in round_ids:
    self.time_monitor.record_tableapi_start(table["name"], round_id)

# In the shake command section:
self.logger.info(f"Shake command with round ID: {first_round_id}")
await self.shaker_controller.shake(first_round_id)
self.time_monitor.record_shaker_start("SBO-001", first_round_id)

# After shaker reaches S0 state:
if s0_reached:
    self.time_monitor.record_shaker_s0("SBO-001", first_round_id)

# In the detect command section:
detect_time = int(time.time() * 1000)
success, dice_result = await self.idp_controller.detect(first_round_id)
self.time_monitor.record_idp_send("SBO-001", first_round_id)

# After successful detection:
if is_valid_result:
    self.time_monitor.record_idp_receive("SBO-001", first_round_id, dice_result)

    # After successful deal_post calls:
    for table, round_id, _ in round_ids:
        self.time_monitor.record_tableapi_deal(table["name"], round_id, dice_result)

    # After successful finish_post calls:
    for table, round_id, _ in round_ids:
        self.time_monitor.record_tableapi_finish(table["name"], round_id)

# In SDPGame.cleanup method:
async def cleanup(self):
    """Cleanup all resources"""
    self.logger.info("Cleaning up resources")

    # Cleanup time monitor
    if hasattr(self, 'time_monitor'):
        await self.time_monitor.cleanup()

    # ... existing cleanup code ...

# For bet stop countdown, add in _bet_stop_countdown method:
async def _bet_stop_countdown(self, table, round_id, bet_period):
    """Countdown and call bet stop for a table (non-blocking)"""
    try:
        await asyncio.sleep(bet_period)

        result = await betStop_round_for_table(table, self.token)

        if result[1]:
            # Record bet stop event
            if hasattr(self, 'time_monitor'):
                self.time_monitor.record_tableapi_betstop(table["name"], round_id)

        # ... existing code ...
'''

    print("Integration code for main_sicbo.py:")
    print(integration_code)

async def demo_integration():
    """Demonstrate the Sicbo integration functionality."""
    print("🚀 Starting Sicbo Time Monitor Integration Demo")

    # Initialize integration
    monitor = SicboTimeMonitorIntegration()
    await monitor.initialize()

    try:
        # Simulate a complete Sicbo round
        table = "SBO-001"
        round_id = "DEMO123"
        dice_result = [3, 4, 5]

        print(f"\n📋 Simulating Sicbo round: {table} - {round_id}")

        # Simulate TableAPI events
        monitor.record_tableapi_start(table, round_id)
        await asyncio.sleep(0.1)

        monitor.record_tableapi_betstop(table, round_id)
        await asyncio.sleep(0.1)

        # Simulate shaker events
        monitor.record_shaker_start(table, round_id, "/cycle/?pattern=0&parameter1=10")
        await asyncio.sleep(0.1)

        monitor.record_shaker_s0(table, round_id)
        await asyncio.sleep(0.1)

        # Simulate IDP events
        monitor.record_idp_send(table, round_id, "detect")
        await asyncio.sleep(0.1)

        monitor.record_idp_receive(table, round_id, dice_result)
        await asyncio.sleep(0.1)

        # Complete TableAPI events
        monitor.record_tableapi_deal(table, round_id, dice_result)
        await asyncio.sleep(0.1)

        monitor.record_tableapi_finish(table, round_id)

        # Wait for processing
        await asyncio.sleep(2.0)

        # Get statistics
        stats = monitor.time_monitor.get_statistics()
        print(f"\n📊 Statistics: {stats}")

    finally:
        await monitor.cleanup()

    print("✅ Sicbo demo completed")

if __name__ == "__main__":
    print("Sicbo Time Monitor Integration Examples")
    print("=" * 50)

    print("\n1. Integration with main_sicbo.py:")
    integrate_with_main_sicbo()

    print("\n2. Running demo...")
    asyncio.run(demo_integration())
