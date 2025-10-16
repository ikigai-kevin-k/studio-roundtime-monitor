"""
Main time monitor orchestrator for Studio Round Time Monitor.

Coordinates all monitoring components and provides the main interface
for time monitoring functionality.
"""

import asyncio
from typing import Dict, List, Optional, Any
import structlog

from .event_system import EventSystem, EventType
from .interval_calculator import IntervalCalculator, IntervalType, IntervalData
from ..monitors.tableapi_monitor import TableAPIMonitor
from ..monitors.roulette_monitor import RouletteMonitor
from ..monitors.sicbo_monitor import SicboMonitor
from ..storage.json_storage import JSONStorage
from ..utils.config import MonitorConfig

logger = structlog.get_logger(__name__)

class TimeMonitor:
    """
    Main time monitoring orchestrator.

    Coordinates all monitoring components and provides a unified interface
    for time monitoring functionality.
    """

    def __init__(self, config: MonitorConfig):
        """
        Initialize the time monitor.

        Args:
            config: Monitor configuration
        """
        self.config = config
        self.event_system = EventSystem()
        self.interval_calculator = IntervalCalculator(max_history=config.max_history)

        # Initialize monitors
        self.tableapi_monitor = None
        self.roulette_monitor = None
        self.sicbo_monitor = None

        # Initialize storage
        self.storage = JSONStorage(config.storage.path)

        # Running state
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Setup monitors based on configuration
        self._setup_monitors()

    def _setup_monitors(self) -> None:
        """Setup monitors based on configuration."""
        if self.config.monitor.tableapi_enabled:
            self.tableapi_monitor = TableAPIMonitor(self.event_system, self.interval_calculator)
            logger.info("TableAPI monitor initialized")

        if self.config.monitor.roulette_enabled:
            self.roulette_monitor = RouletteMonitor(self.event_system, self.interval_calculator)
            logger.info("Roulette monitor initialized")

        if self.config.monitor.sicbo_enabled:
            self.sicbo_monitor = SicboMonitor(self.event_system, self.interval_calculator)
            logger.info("Sicbo monitor initialized")

    async def start(self) -> None:
        """Start the time monitoring system."""
        if self._running:
            logger.warning("Time monitor is already running")
            return

        self._running = True

        # Start event system
        await self.event_system.start()

        # Start monitors
        if self.tableapi_monitor:
            await self.tableapi_monitor.start()

        if self.roulette_monitor:
            await self.roulette_monitor.start()

        if self.sicbo_monitor:
            await self.sicbo_monitor.start()

        # Start interval processing task
        self._task = asyncio.create_task(self._process_intervals())

        logger.info("Time monitor started successfully")

    async def stop(self) -> None:
        """Stop the time monitoring system."""
        if not self._running:
            logger.warning("Time monitor is not running")
            return

        self._running = False

        # Stop monitors
        if self.tableapi_monitor:
            await self.tableapi_monitor.stop()

        if self.roulette_monitor:
            await self.roulette_monitor.stop()

        if self.sicbo_monitor:
            await self.sicbo_monitor.stop()

        # Stop interval processing task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Stop event system
        await self.event_system.stop()

        logger.info("Time monitor stopped")

    async def _process_intervals(self) -> None:
        """Process intervals and save to storage."""
        while self._running:
            try:
                # Get all recent intervals
                all_intervals = []
                for interval_type in IntervalType:
                    intervals = self.interval_calculator.get_intervals(interval_type, limit=10)
                    all_intervals.extend(intervals)

                # Save intervals to storage if any exist
                if all_intervals:
                    await self.storage.save_intervals(all_intervals)

                # Wait before next processing cycle
                await asyncio.sleep(self.config.processing_interval)

            except Exception as e:
                logger.error("Error processing intervals", error=str(e))
                await asyncio.sleep(1.0)  # Brief pause before retry

    def publish_event(self,
                     event_type: EventType,
                     game_type: str,
                     table: str,
                     round_id: str,
                     **data) -> None:
        """
        Publish an event for monitoring.

        Args:
            event_type: Type of the event
            game_type: Type of game ('roulette', 'sicbo', etc.)
            table: Table identifier
            round_id: Round identifier
            **data: Additional event data
        """
        self.event_system.publish_simple(
            event_type=event_type,
            game_type=game_type,
            table=table,
            round_id=round_id,
            **data
        )

    def record_tableapi_event(self,
                            event_type: str,
                            game_type: str,
                            table: str,
                            round_id: str,
                            timestamp: Optional[float] = None) -> List[IntervalData]:
        """
        Record a TableAPI event and calculate intervals.

        Args:
            event_type: Type of TableAPI event
            game_type: Type of game
            table: Table identifier
            round_id: Round identifier
            timestamp: Event timestamp (defaults to current time)

        Returns:
            List of newly calculated intervals
        """
        return self.interval_calculator.record_event(
            event_type=event_type,
            game_type=game_type,
            table=table,
            round_id=round_id,
            timestamp=timestamp
        )

    def record_roulette_event(self,
                            event_type: str,
                            game_type: str,
                            table: str,
                            round_id: str,
                            timestamp: Optional[float] = None) -> List[IntervalData]:
        """
        Record a Roulette device event and calculate intervals.

        Args:
            event_type: Type of Roulette event
            game_type: Type of game
            table: Table identifier
            round_id: Round identifier
            timestamp: Event timestamp (defaults to current time)

        Returns:
            List of newly calculated intervals
        """
        return self.interval_calculator.record_event(
            event_type=event_type,
            game_type=game_type,
            table=table,
            round_id=round_id,
            timestamp=timestamp
        )

    def record_sicbo_event(self,
                         event_type: str,
                         game_type: str,
                         table: str,
                         round_id: str,
                         timestamp: Optional[float] = None) -> List[IntervalData]:
        """
        Record a Sicbo device event and calculate intervals.

        Args:
            event_type: Type of Sicbo event
            game_type: Type of game
            table: Table identifier
            round_id: Round identifier
            timestamp: Event timestamp (defaults to current time)

        Returns:
            List of newly calculated intervals
        """
        return self.interval_calculator.record_event(
            event_type=event_type,
            game_type=game_type,
            table=table,
            round_id=round_id,
            timestamp=timestamp
        )

    def get_statistics(self, interval_type: Optional[IntervalType] = None) -> Dict[str, Any]:
        """
        Get statistics for interval types.

        Args:
            interval_type: Specific interval type (None for all types)

        Returns:
            Statistics data
        """
        if interval_type is None:
            all_stats = self.interval_calculator.get_all_statistics()
            return {stats.interval_type.value: stats.to_dict() for stats in all_stats.values()}
        else:
            stats = self.interval_calculator.get_statistics(interval_type)
            return {stats.interval_type.value: stats.to_dict()}

    def get_recent_intervals(self,
                           interval_type: IntervalType,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent intervals for a specific type.

        Args:
            interval_type: Type of interval
            limit: Maximum number of intervals to return

        Returns:
            List of interval data dictionaries
        """
        intervals = self.interval_calculator.get_intervals(interval_type, limit)
        return [interval.to_dict() for interval in intervals]

    def detect_anomalies(self,
                        interval_type: IntervalType,
                        threshold_multiplier: float = 2.0) -> List[Dict[str, Any]]:
        """
        Detect anomalous intervals.

        Args:
            interval_type: Type of interval to check
            threshold_multiplier: Multiplier for standard deviation threshold

        Returns:
            List of anomalous interval data dictionaries
        """
        anomalies = self.interval_calculator.detect_anomalies(
            interval_type, threshold_multiplier
        )
        return [anomaly.to_dict() for anomaly in anomalies]

    async def export_data(self,
                         output_path: str,
                         format: str = "json",
                         interval_types: Optional[List[IntervalType]] = None) -> None:
        """
        Export monitoring data to file.

        Args:
            output_path: Path to output file
            format: Export format ('json' or 'csv')
            interval_types: Specific interval types to export (None for all)
        """
        if interval_types is None:
            interval_types = list(IntervalType)

        all_intervals = []
        for interval_type in interval_types:
            intervals = self.interval_calculator.get_intervals(interval_type)
            all_intervals.extend(intervals)

        if format == "json":
            await self.storage.export_json(all_intervals, output_path)
        elif format == "csv":
            await self.storage.export_csv(all_intervals, output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        logger.info("Data exported successfully",
                   output_path=output_path,
                   format=format,
                   interval_count=len(all_intervals))

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the monitoring system.

        Returns:
            Health status information
        """
        return {
            "running": self._running,
            "event_system_subscribers": {
                event_type.value: self.event_system.get_subscriber_count(event_type)
                for event_type in EventType
            },
            "interval_statistics": {
                interval_type.value: {
                    "count": stats.count,
                    "avg_duration": stats.avg_duration,
                    "recent_anomalies": len(self.interval_calculator.detect_anomalies(interval_type))
                }
                for interval_type, stats in self.interval_calculator.get_all_statistics().items()
            },
            "monitors": {
                "tableapi": self.tableapi_monitor is not None,
                "roulette": self.roulette_monitor is not None,
                "sicbo": self.sicbo_monitor is not None
            }
        }
