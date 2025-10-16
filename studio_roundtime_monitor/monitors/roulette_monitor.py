"""
Roulette monitor for Studio Round Time Monitor.

Monitors Roulette device timing events and calculates intervals between
*X;2 (ball launch), *X;3 (ball landing), *X;4 (detection), and *X;5 (result) events.
"""

from typing import Dict, List, Optional
import structlog

from ..core.event_system import EventSystem, EventType, GameEvent
from ..core.interval_calculator import IntervalCalculator, IntervalType

logger = structlog.get_logger(__name__)

class RouletteMonitor:
    """
    Monitor for Roulette device timing events.

    Tracks the timing of Roulette device events (*X;2, *X;3, *X;4, *X;5)
    and calculates intervals between different device operations.
    """

    def __init__(self, event_system: EventSystem, interval_calculator: IntervalCalculator):
        """
        Initialize the Roulette monitor.

        Args:
            event_system: Event system for communication
            interval_calculator: Calculator for interval processing
        """
        self.event_system = event_system
        self.interval_calculator = interval_calculator
        self._running = False

        # Subscribe to Roulette device events
        self.event_system.subscribe_async(EventType.ROULETTE_X2, self._handle_x2_event)
        self.event_system.subscribe_async(EventType.ROULETTE_X3, self._handle_x3_event)
        self.event_system.subscribe_async(EventType.ROULETTE_X4, self._handle_x4_event)
        self.event_system.subscribe_async(EventType.ROULETTE_X5, self._handle_x5_event)

        # Track current round state
        self._current_rounds: Dict[str, Dict[str, float]] = {}  # table_round_id -> event_timestamps

    async def start(self) -> None:
        """Start the Roulette monitor."""
        if self._running:
            logger.warning("Roulette monitor is already running")
            return

        self._running = True
        logger.info("Roulette monitor started")

    async def stop(self) -> None:
        """Stop the Roulette monitor."""
        if not self._running:
            logger.warning("Roulette monitor is not running")
            return

        self._running = False
        logger.info("Roulette monitor stopped")

    async def _handle_x2_event(self, event: GameEvent) -> None:
        """Handle *X;2 event (ball launch)."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="roulette_x2",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["x2"] = event.timestamp

        # Log the event
        logger.info("Roulette *X;2 event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_x3_event(self, event: GameEvent) -> None:
        """Handle *X;3 event (ball landing)."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="roulette_x3",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["x3"] = event.timestamp

        # Log the event
        logger.info("Roulette *X;3 event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_x4_event(self, event: GameEvent) -> None:
        """Handle *X;4 event (detection)."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="roulette_x4",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["x4"] = event.timestamp

        # Log the event
        logger.info("Roulette *X;4 event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_x5_event(self, event: GameEvent) -> None:
        """Handle *X;5 event (result announcement)."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="roulette_x5",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["x5"] = event.timestamp

        # Log the event
        logger.info("Roulette *X;5 event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

        # Clean up completed round data
        self._cleanup_round(round_key)

    async def _process_interval(self, interval) -> None:
        """Process a calculated interval."""
        # Check for anomalies
        anomalies = self.interval_calculator.detect_anomalies(interval.interval_type)
        if interval in anomalies:
            logger.warning("Anomalous interval detected",
                         interval_type=interval.interval_type.value,
                         duration=interval.duration,
                         table=interval.table,
                         round_id=interval.round_id)

        # Log interval information
        logger.info("Roulette interval calculated",
                   interval_type=interval.interval_type.value,
                   duration=interval.duration,
                   table=interval.table,
                   round_id=interval.round_id)

    def _cleanup_round(self, round_key: str) -> None:
        """Clean up completed round data."""
        if round_key in self._current_rounds:
            del self._current_rounds[round_key]
            logger.debug("Cleaned up round data", round_key=round_key)

    def get_current_rounds(self) -> Dict[str, Dict[str, float]]:
        """Get current active rounds and their timestamps."""
        return self._current_rounds.copy()

    def get_round_duration(self, table: str, round_id: str) -> Optional[float]:
        """
        Get the total duration of a round if it's complete.

        Args:
            table: Table identifier
            round_id: Round identifier

        Returns:
            Total duration in seconds, or None if round is not complete
        """
        round_key = f"{table}_{round_id}"
        if round_key not in self._current_rounds:
            return None

        events = self._current_rounds[round_key]
        required_events = ["x2", "x3", "x4", "x5"]

        if not all(event in events for event in required_events):
            return None  # Round not complete

        return events["x5"] - events["x2"]

    def get_partial_intervals(self, table: str, round_id: str) -> Dict[str, float]:
        """
        Get partial intervals for a round that may not be complete.

        Args:
            table: Table identifier
            round_id: Round identifier

        Returns:
            Dictionary of calculated partial intervals
        """
        round_key = f"{table}_{round_id}"
        if round_key not in self._current_rounds:
            return {}

        events = self._current_rounds[round_key]
        intervals = {}

        # Calculate available intervals
        if "x2" in events and "x3" in events:
            intervals["*X;2-to-*X;3"] = events["x3"] - events["x2"]

        if "x3" in events and "x4" in events:
            intervals["*X;3-to-*X;4"] = events["x4"] - events["x3"]

        if "x4" in events and "x5" in events:
            intervals["*X;4-to-*X;5"] = events["x5"] - events["x4"]

        return intervals

    def get_statistics(self) -> Dict[str, any]:
        """Get Roulette-specific statistics."""
        stats = self.interval_calculator.get_all_statistics()

        roulette_stats = {}
        for interval_type in [IntervalType.X2_TO_X3,
                             IntervalType.X3_TO_X4,
                             IntervalType.X4_TO_X5,
                             IntervalType.X5_TO_X2]:
            if interval_type in stats:
                roulette_stats[interval_type.value] = stats[interval_type].to_dict()

        return {
            "intervals": roulette_stats,
            "active_rounds": len(self._current_rounds),
            "current_rounds": self._current_rounds
        }

    def get_device_performance_metrics(self) -> Dict[str, any]:
        """
        Get device-specific performance metrics.

        Returns:
            Performance metrics for Roulette device operations
        """
        stats = self.get_statistics()

        # Calculate performance indicators
        performance_metrics = {
            "ball_flight_time": {
                "avg": stats["intervals"].get("*X;2-to-*X;3", {}).get("avg_duration", 0),
                "min": stats["intervals"].get("*X;2-to-*X;3", {}).get("min_duration", 0),
                "max": stats["intervals"].get("*X;2-to-*X;3", {}).get("max_duration", 0),
                "std_dev": stats["intervals"].get("*X;2-to-*X;3", {}).get("std_deviation", 0)
            },
            "detection_time": {
                "avg": stats["intervals"].get("*X;3-to-*X;4", {}).get("avg_duration", 0),
                "min": stats["intervals"].get("*X;3-to-*X;4", {}).get("min_duration", 0),
                "max": stats["intervals"].get("*X;3-to-*X;4", {}).get("max_duration", 0),
                "std_dev": stats["intervals"].get("*X;3-to-*X;4", {}).get("std_deviation", 0)
            },
            "result_processing_time": {
                "avg": stats["intervals"].get("*X;4-to-*X;5", {}).get("avg_duration", 0),
                "min": stats["intervals"].get("*X;4-to-*X;5", {}).get("min_duration", 0),
                "max": stats["intervals"].get("*X;4-to-*X;5", {}).get("max_duration", 0),
                "std_dev": stats["intervals"].get("*X;4-to-*X;5", {}).get("std_deviation", 0)
            },
            "round_cycle_time": {
                "avg": stats["intervals"].get("*X;5-to-*X;2", {}).get("avg_duration", 0),
                "min": stats["intervals"].get("*X;5-to-*X;2", {}).get("min_duration", 0),
                "max": stats["intervals"].get("*X;5-to-*X;2", {}).get("max_duration", 0),
                "std_dev": stats["intervals"].get("*X;5-to-*X;2", {}).get("std_deviation", 0)
            }
        }

        return performance_metrics
