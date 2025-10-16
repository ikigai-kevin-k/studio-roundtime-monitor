"""
Unit tests for monitor components.

Tests the functionality of TableAPI, Roulette, and Sicbo monitors.
"""

import pytest
import asyncio
import time

from studio_roundtime_monitor.core.event_system import EventSystem,
    EventType,
    GameEvent
from studio_roundtime_monitor.core.interval_calculator import IntervalCalculator
from studio_roundtime_monitor.monitors.tableapi_monitor import TableAPIMonitor
from studio_roundtime_monitor.monitors.roulette_monitor import RouletteMonitor
from studio_roundtime_monitor.monitors.sicbo_monitor import SicboMonitor

class TestTableAPIMonitor:
    """Test TableAPI monitor functionality."""

    @pytest.fixture
    async def monitor_setup(self):
        """Setup monitor for testing."""
        event_system = EventSystem()
        interval_calculator = IntervalCalculator()
        monitor = TableAPIMonitor(event_system, interval_calculator)

        await event_system.start()
        await monitor.start()

        yield monitor, event_system, interval_calculator

        await monitor.stop()
        await event_system.stop()

    @pytest.mark.asyncio
    async def test_tableapi_start_event(self, monitor_setup):
        """Test TableAPI start event handling."""
        monitor, event_system, interval_calculator = await monitor_setup

        # Create and publish start event
        event = GameEvent(
            event_type=EventType.TABLEAPI_START,
            timestamp=time.time(),
            game_type="roulette",
            table="PRD",
            round_id="12345"
        )

        event_system.publish(event)
        await asyncio.sleep(0.1)  # Allow async processing

        # Check that event was recorded
        rounds = monitor.get_current_rounds()
        assert "PRD_12345" in rounds
        assert "start" in rounds["PRD_12345"]

    @pytest.mark.asyncio
    async def test_tableapi_complete_round(self, monitor_setup):
        """Test complete TableAPI round timing."""
        monitor, event_system, interval_calculator = await monitor_setup

        base_time = time.time()

        # Simulate complete round
        events = [
            (EventType.TABLEAPI_START, base_time),
            (EventType.TABLEAPI_BETSTOP, base_time + 15.0),
            (EventType.TABLEAPI_DEAL, base_time + 18.0),
            (EventType.TABLEAPI_FINISH, base_time + 20.0),
        ]

        for event_type, timestamp in events:
            event = GameEvent(
                event_type=event_type,
                timestamp=timestamp,
                game_type="roulette",
                table="PRD",
                round_id="12345"
            )
            event_system.publish(event)
            await asyncio.sleep(0.1)

        # Check round duration
        duration = monitor.get_round_duration("PRD", "12345")
        assert duration is not None
        assert abs(duration - 20.0) < 0.1

    @pytest.mark.asyncio
    async def test_partial_intervals(self, monitor_setup):
        """Test partial interval calculation."""
        monitor, event_system, interval_calculator = await monitor_setup

        base_time = time.time()

        # Simulate partial round
        events = [
            (EventType.TABLEAPI_START, base_time),
            (EventType.TABLEAPI_BETSTOP, base_time + 15.0),
            (EventType.TABLEAPI_DEAL, base_time + 18.0),
        ]

        for event_type, timestamp in events:
            event = GameEvent(
                event_type=event_type,
                timestamp=timestamp,
                game_type="roulette",
                table="PRD",
                round_id="12345"
            )
            event_system.publish(event)
            await asyncio.sleep(0.1)

        # Check partial intervals
        intervals = monitor.get_partial_intervals("PRD", "12345")
        assert "start-to-betstop" in intervals
        assert "betstop-to-deal" in intervals
        assert abs(intervals["start-to-betstop"] - 15.0) < 0.1
        assert abs(intervals["betstop-to-deal"] - 3.0) < 0.1

class TestRouletteMonitor:
    """Test Roulette monitor functionality."""

    @pytest.fixture
    async def monitor_setup(self):
        """Setup monitor for testing."""
        event_system = EventSystem()
        interval_calculator = IntervalCalculator()
        monitor = RouletteMonitor(event_system, interval_calculator)

        await event_system.start()
        await monitor.start()

        yield monitor, event_system, interval_calculator

        await monitor.stop()
        await event_system.stop()

    @pytest.mark.asyncio
    async def test_roulette_x2_event(self, monitor_setup):
        """Test Roulette *X;2 event handling."""
        monitor, event_system, interval_calculator = await monitor_setup

        # Create and publish *X;2 event
        event = GameEvent(
            event_type=EventType.ROULETTE_X2,
            timestamp=time.time(),
            game_type="roulette",
            table="PRD",
            round_id="12345"
        )

        event_system.publish(event)
        await asyncio.sleep(0.1)

        # Check that event was recorded
        rounds = monitor.get_current_rounds()
        assert "PRD_12345" in rounds
        assert "x2" in rounds["PRD_12345"]

    @pytest.mark.asyncio
    async def test_roulette_complete_cycle(self, monitor_setup):
        """Test complete Roulette device cycle."""
        monitor, event_system, interval_calculator = await monitor_setup

        base_time = time.time()

        # Simulate complete cycle
        events = [
            (EventType.ROULETTE_X2, base_time),
            (EventType.ROULETTE_X3, base_time + 8.0),
            (EventType.ROULETTE_X4, base_time + 10.0),
            (EventType.ROULETTE_X5, base_time + 12.0),
        ]

        for event_type, timestamp in events:
            event = GameEvent(
                event_type=event_type,
                timestamp=timestamp,
                game_type="roulette",
                table="PRD",
                round_id="12345"
            )
            event_system.publish(event)
            await asyncio.sleep(0.1)

        # Check device performance metrics
        metrics = monitor.get_device_performance_metrics()
        assert "ball_flight_time" in metrics
        assert "detection_time" in metrics
        assert "result_processing_time" in metrics

class TestSicboMonitor:
    """Test Sicbo monitor functionality."""

    @pytest.fixture
    async def monitor_setup(self):
        """Setup monitor for testing."""
        event_system = EventSystem()
        interval_calculator = IntervalCalculator()
        monitor = SicboMonitor(event_system, interval_calculator)

        await event_system.start()
        await monitor.start()

        yield monitor, event_system, interval_calculator

        await monitor.stop()
        await event_system.stop()

    @pytest.mark.asyncio
    async def test_sicbo_shaker_events(self, monitor_setup):
        """Test Sicbo shaker event handling."""
        monitor, event_system, interval_calculator = await monitor_setup

        base_time = time.time()

        # Simulate shaker cycle
        events = [
            (EventType.SICBO_SHAKER_STOP, base_time),
            (EventType.SICBO_SHAKER_START, base_time + 2.0),
            (EventType.SICBO_SHAKER_S0, base_time + 12.0),
            (EventType.SICBO_SHAKER_STOP, base_time + 13.0),
        ]

        for event_type, timestamp in events:
            event = GameEvent(
                event_type=event_type,
                timestamp=timestamp,
                game_type="sicbo",
                table="SBO-001",
                round_id="12345"
            )
            event_system.publish(event)
            await asyncio.sleep(0.1)

        # Check shaker state info
        state_info = monitor.get_shaker_state_info("SBO-001", "12345")
        assert state_info["status"] == "active"
        assert state_info["has_shaker_start"]
        assert state_info["has_shaker_stop"]
        assert state_info["has_shaker_s0"]

    @pytest.mark.asyncio
    async def test_sicbo_idp_events(self, monitor_setup):
        """Test Sicbo IDP event handling."""
        monitor, event_system, interval_calculator = await monitor_setup

        base_time = time.time()

        # Simulate IDP cycle
        events = [
            (EventType.SICBO_IDP_SEND, base_time),
            (EventType.SICBO_IDP_RECEIVE, base_time + 1.5),
        ]

        for event_type, timestamp in events:
            event = GameEvent(
                event_type=event_type,
                timestamp=timestamp,
                game_type="sicbo",
                table="SBO-001",
                round_id="12345"
            )
            event_system.publish(event)
            await asyncio.sleep(0.1)

        # Check device performance metrics
        metrics = monitor.get_device_performance_metrics()
        assert "idp_processing_time" in metrics
        assert "idp_cycle_time" in metrics

class TestIntervalCalculator:
    """Test interval calculator functionality."""

    @pytest.fixture
    def calculator(self):
        """Setup interval calculator for testing."""
        return IntervalCalculator(max_history=100)

    def test_tableapi_interval_calculation(self, calculator):
        """Test TableAPI interval calculation."""
        base_time = time.time()

        # Record events
        calculator.record_event("tableapi_start", "roulette", "PRD", "12345", base_time)
        calculator.record_event("tableapi_betstop", "roulette", "PRD", "12345", base_time + 15.0)
        calculator.record_event("tableapi_deal", "roulette", "PRD", "12345", base_time + 18.0)

        # Finish event should trigger interval calculation
        intervals = calculator.record_event("tableapi_finish", "roulette", "PRD", "12345", base_time + 20.0)

        assert len(intervals) == 3  # start-to-betstop, betstop-to-deal, deal-to-finish
        assert intervals[0].duration == 15.0
        assert intervals[1].duration == 3.0
        assert intervals[2].duration == 2.0

    def test_anomaly_detection(self, calculator):
        """Test anomaly detection functionality."""
        base_time = time.time()

        # Record normal intervals
        for i in range(5):
            calculator.record_event("tableapi_start", "roulette", "PRD", f"1234{i}", base_time + i * 20)
            calculator.record_event("tableapi_finish", "roulette", "PRD", f"1234{i}", base_time + i * 20 + 10)

        # Record anomalous interval (much longer)
        calculator.record_event("tableapi_start", "roulette", "PRD", "99999", base_time + 100)
        calculator.record_event("tableapi_finish", "roulette", "PRD", "99999", base_time + 150)  # 50 seconds

        # Check for anomalies
        from studio_roundtime_monitor.core.interval_calculator import IntervalType
        anomalies = calculator.detect_anomalies(IntervalType.FINISH_TO_START)
        assert len(anomalies) > 0  # Should detect the anomalous interval

    def test_statistics_calculation(self, calculator):
        """Test statistics calculation."""
        base_time = time.time()

        # Record multiple intervals
        for i in range(10):
            calculator.record_event("tableapi_start", "roulette", "PRD", f"1234{i}", base_time + i * 20)
            calculator.record_event("tableapi_finish", "roulette", "PRD", f"1234{i}", base_time + i * 20 + 10)

        # Check statistics
        from studio_roundtime_monitor.core.interval_calculator import IntervalType
        stats = calculator.get_statistics(IntervalType.FINISH_TO_START)
        assert stats["count"] == 10
        assert stats["avg_duration"] == 10.0
        assert stats["min_duration"] == 10.0
        assert stats["max_duration"] == 10.0

if __name__ == "__main__":
    pytest.main([__file__])
