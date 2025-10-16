"""
TableAPI monitor for Studio Round Time Monitor.

Monitors TableAPI call timing and calculates intervals between
start, betstop, deal, and finish operations.
"""

from typing import Dict, List, Optional
import structlog

from ..core.event_system import EventSystem, EventType, GameEvent
from ..core.interval_calculator import IntervalCalculator, IntervalType

logger = structlog.get_logger(__name__)

class TableAPIMonitor:
    """
    Monitor for TableAPI timing events.

    Tracks the timing of TableAPI calls and calculates intervals
    between different API operations.
    """

    def __init__(self, event_system: EventSystem, interval_calculator: IntervalCalculator):
        """
        Initialize the TableAPI monitor.

        Args:
            event_system: Event system for communication
            interval_calculator: Calculator for interval processing
        """
        self.event_system = event_system
        self.interval_calculator = interval_calculator
        self._running = False

        # Subscribe to TableAPI events
        self.event_system.subscribe_async(EventType.TABLEAPI_START, self._handle_start_event)
        self.event_system.subscribe_async(EventType.TABLEAPI_BETSTOP, self._handle_betstop_event)
        self.event_system.subscribe_async(EventType.TABLEAPI_DEAL, self._handle_deal_event)
        self.event_system.subscribe_async(EventType.TABLEAPI_FINISH, self._handle_finish_event)

        # Track current round state
        self._current_rounds: Dict[str, Dict[str, float]] = {}  # table_round_id -> event_timestamps

    async def start(self) -> None:
        """Start the TableAPI monitor."""
        if self._running:
            logger.warning("TableAPI monitor is already running")
            return

        self._running = True
        logger.info("TableAPI monitor started")

    async def stop(self) -> None:
        """Stop the TableAPI monitor."""
        if not self._running:
            logger.warning("TableAPI monitor is not running")
            return

        self._running = False
        logger.info("TableAPI monitor stopped")

    async def _handle_start_event(self, event: GameEvent) -> None:
        """Handle TableAPI start event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="tableapi_start",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["start"] = event.timestamp

        # Log the event
        logger.info("TableAPI start event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_betstop_event(self, event: GameEvent) -> None:
        """Handle TableAPI betstop event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="tableapi_betstop",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["betstop"] = event.timestamp

        # Log the event
        logger.info("TableAPI betstop event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_deal_event(self, event: GameEvent) -> None:
        """Handle TableAPI deal event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="tableapi_deal",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["deal"] = event.timestamp

        # Log the event
        logger.info("TableAPI deal event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_finish_event(self, event: GameEvent) -> None:
        """Handle TableAPI finish event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="tableapi_finish",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["finish"] = event.timestamp

        # Log the event
        logger.info("TableAPI finish event recorded",
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
        logger.info("TableAPI interval calculated",
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
        required_events = ["start", "betstop", "deal", "finish"]

        if not all(event in events for event in required_events):
            return None  # Round not complete

        return events["finish"] - events["start"]

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
        if "start" in events and "betstop" in events:
            intervals["start-to-betstop"] = events["betstop"] - events["start"]

        if "betstop" in events and "deal" in events:
            intervals["betstop-to-deal"] = events["deal"] - events["betstop"]

        if "deal" in events and "finish" in events:
            intervals["deal-to-finish"] = events["finish"] - events["deal"]

        return intervals

    def get_statistics(self) -> Dict[str, any]:
        """Get TableAPI-specific statistics."""
        stats = self.interval_calculator.get_all_statistics()

        tableapi_stats = {}
        for interval_type in [IntervalType.START_TO_BETSTOP,
                             IntervalType.BETSTOP_TO_DEAL,
                             IntervalType.DEAL_TO_FINISH,
                             IntervalType.FINISH_TO_START]:
            if interval_type in stats:
                tableapi_stats[interval_type.value] = stats[interval_type].to_dict()

        return {
            "intervals": tableapi_stats,
            "active_rounds": len(self._current_rounds),
            "current_rounds": self._current_rounds
        }
