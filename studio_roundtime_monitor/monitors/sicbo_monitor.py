"""
Sicbo monitor for Studio Round Time Monitor.

Monitors Sicbo device timing events including shaker operations and IDP
detection timing.
"""

from typing import Dict, List, Optional
import structlog

from ..core.event_system import EventSystem, EventType, GameEvent
from ..core.interval_calculator import IntervalCalculator, IntervalType

logger = structlog.get_logger(__name__)

class SicboMonitor:
    """
    Monitor for Sicbo device timing events.

    Tracks the timing of Sicbo shaker and IDP operations and calculates
    intervals between different device operations.
    """

    def __init__(self, event_system: EventSystem, interval_calculator: IntervalCalculator):
        """
        Initialize the Sicbo monitor.

        Args:
            event_system: Event system for communication
            interval_calculator: Calculator for interval processing
        """
        self.event_system = event_system
        self.interval_calculator = interval_calculator
        self._running = False

        # Subscribe to Sicbo device events
        self.event_system.subscribe_async(EventType.SICBO_SHAKER_START, self._handle_shaker_start_event)
        self.event_system.subscribe_async(EventType.SICBO_SHAKER_STOP, self._handle_shaker_stop_event)
        self.event_system.subscribe_async(EventType.SICBO_SHAKER_S0, self._handle_shaker_s0_event)
        self.event_system.subscribe_async(EventType.SICBO_IDP_SEND, self._handle_idp_send_event)
        self.event_system.subscribe_async(EventType.SICBO_IDP_RECEIVE, self._handle_idp_receive_event)

        # Track current round state
        self._current_rounds: Dict[str, Dict[str, float]] = {}  # table_round_id -> event_timestamps

    async def start(self) -> None:
        """Start the Sicbo monitor."""
        if self._running:
            logger.warning("Sicbo monitor is already running")
            return

        self._running = True
        logger.info("Sicbo monitor started")

    async def stop(self) -> None:
        """Stop the Sicbo monitor."""
        if not self._running:
            logger.warning("Sicbo monitor is not running")
            return

        self._running = False
        logger.info("Sicbo monitor stopped")

    async def _handle_shaker_start_event(self, event: GameEvent) -> None:
        """Handle shaker start event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="sicbo_shaker_start",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["shaker_start"] = event.timestamp

        # Log the event
        logger.info("Sicbo shaker start event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_shaker_stop_event(self, event: GameEvent) -> None:
        """Handle shaker stop event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="sicbo_shaker_stop",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["shaker_stop"] = event.timestamp

        # Log the event
        logger.info("Sicbo shaker stop event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_shaker_s0_event(self, event: GameEvent) -> None:
        """Handle shaker S0 state event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["shaker_s0"] = event.timestamp

        # Log the event
        logger.info("Sicbo shaker S0 event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp)

    async def _handle_idp_send_event(self, event: GameEvent) -> None:
        """Handle IDP send event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="sicbo_idp_send",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["idp_send"] = event.timestamp

        # Log the event
        logger.info("Sicbo IDP send event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

    async def _handle_idp_receive_event(self, event: GameEvent) -> None:
        """Handle IDP receive event."""
        if not self._running:
            return

        round_key = f"{event.table}_{event.round_id}"

        # Record the event
        intervals = self.interval_calculator.record_event(
            event_type="sicbo_idp_receive",
            game_type=event.game_type,
            table=event.table,
            round_id=event.round_id,
            timestamp=event.timestamp
        )

        # Store timestamp for this round
        if round_key not in self._current_rounds:
            self._current_rounds[round_key] = {}
        self._current_rounds[round_key]["idp_receive"] = event.timestamp

        # Log the event
        logger.info("Sicbo IDP receive event recorded",
                   table=event.table,
                   round_id=event.round_id,
                   timestamp=event.timestamp,
                   intervals_calculated=len(intervals))

        # Process any calculated intervals
        for interval in intervals:
            await self._process_interval(interval)

        # Clean up completed round data (assuming IDP receive completes the round)
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
        logger.info("Sicbo interval calculated",
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

        # Check if we have both shaker start and IDP receive (indicating complete round)
        if "shaker_start" in events and "idp_receive" in events:
            return events["idp_receive"] - events["shaker_start"]

        return None

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

        # Shaker intervals
        if "shaker_stop" in events and "shaker_start" in events:
            intervals["shakerStop-to-shakerShake"] = events["shaker_start"] - events["shaker_stop"]

        if "shaker_start" in events and "shaker_stop" in events:
            intervals["shakerShake-to-shakerStop"] = events["shaker_stop"] - events["shaker_start"]

        # IDP intervals
        if "idp_send" in events and "idp_receive" in events:
            intervals["sendDetect-to-receiveResult"] = events["idp_receive"] - events["idp_send"]

        # S0 to IDP send interval
        if "shaker_s0" in events and "idp_send" in events:
            intervals["shakerS0-to-idpSend"] = events["idp_send"] - events["shaker_s0"]

        return intervals

    def get_statistics(self) -> Dict[str, any]:
        """Get Sicbo-specific statistics."""
        stats = self.interval_calculator.get_all_statistics()

        sicbo_stats = {}
        for interval_type in [IntervalType.SHAKER_STOP_TO_SHAKE,
                             IntervalType.SHAKER_SHAKE_TO_STOP,
                             IntervalType.IDP_SEND_TO_RECEIVE,
                             IntervalType.IDP_RECEIVE_TO_SEND]:
            if interval_type in stats:
                sicbo_stats[interval_type.value] = stats[interval_type].to_dict()

        return {
            "intervals": sicbo_stats,
            "active_rounds": len(self._current_rounds),
            "current_rounds": self._current_rounds
        }

    def get_device_performance_metrics(self) -> Dict[str, any]:
        """
        Get device-specific performance metrics.

        Returns:
            Performance metrics for Sicbo device operations
        """
        stats = self.get_statistics()

        # Calculate performance indicators
        performance_metrics = {
            "shaker_cycle_time": {
                "avg": stats["intervals"].get("shakerStop-to-shakerShake", {}).get("avg_duration", 0),
                "min": stats["intervals"].get("shakerStop-to-shakerShake", {}).get("min_duration", 0),
                "max": stats["intervals"].get("shakerStop-to-shakerShake", {}).get("max_duration", 0),
                "std_dev": stats["intervals"].get("shakerStop-to-shakerShake", {}).get("std_deviation", 0)
            },
            "shaker_operation_time": {
                "avg": stats["intervals"].get("shakerShake-to-shakerStop", {}).get("avg_duration", 0),
                "min": stats["intervals"].get("shakerShake-to-shakerStop", {}).get("min_duration", 0),
                "max": stats["intervals"].get("shakerShake-to-shakerStop", {}).get("max_duration", 0),
                "std_dev": stats["intervals"].get("shakerShake-to-shakerStop", {}).get("std_deviation", 0)
            },
            "idp_processing_time": {
                "avg": stats["intervals"].get("sendDetect-to-receiveResult", {}).get("avg_duration", 0),
                "min": stats["intervals"].get("sendDetect-to-receiveResult", {}).get("min_duration", 0),
                "max": stats["intervals"].get("sendDetect-to-receiveResult", {}).get("max_duration", 0),
                "std_dev": stats["intervals"].get("sendDetect-to-receiveResult", {}).get("std_deviation", 0)
            },
            "idp_cycle_time": {
                "avg": stats["intervals"].get("receiveResult-to-sendDetect", {}).get("avg_duration", 0),
                "min": stats["intervals"].get("receiveResult-to-sendDetect", {}).get("min_duration", 0),
                "max": stats["intervals"].get("receiveResult-to-sendDetect", {}).get("max_duration", 0),
                "std_dev": stats["intervals"].get("receiveResult-to-sendDetect", {}).get("std_deviation", 0)
            }
        }

        return performance_metrics

    def get_shaker_state_info(self, table: str, round_id: str) -> Dict[str, any]:
        """
        Get detailed shaker state information for a round.

        Args:
            table: Table identifier
            round_id: Round identifier

        Returns:
            Shaker state information
        """
        round_key = f"{table}_{round_id}"
        if round_key not in self._current_rounds:
            return {"status": "not_found"}

        events = self._current_rounds[round_key]

        info = {
            "status": "active",
            "events": events.copy(),
            "has_shaker_start": "shaker_start" in events,
            "has_shaker_stop": "shaker_stop" in events,
            "has_shaker_s0": "shaker_s0" in events,
            "has_idp_send": "idp_send" in events,
            "has_idp_receive": "idp_receive" in events
        }

        # Calculate current state
        if "idp_receive" in events:
            info["status"] = "completed"
        elif "shaker_start" in events and "shaker_stop" in events:
            info["status"] = "shaking_completed"
        elif "shaker_start" in events:
            info["status"] = "shaking"
        else:
            info["status"] = "initializing"

        return info
