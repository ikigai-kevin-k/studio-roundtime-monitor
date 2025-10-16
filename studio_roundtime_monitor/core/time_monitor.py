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
from ..storage.csv_storage import CSVStorage
from ..storage.database_storage import DatabaseStorage
from ..storage.telemetry_storage import TelemetryStorageBackend
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

        # Initialize storage based on configuration
        self.storage = self._create_storage(config)

        # Running state
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Setup monitors based on configuration
        self._setup_monitors()

    def _create_storage(self, config: MonitorConfig):
        """Create storage instance based on configuration."""
        storage_type = config.storage.type.lower()
        
        if storage_type == "json":
            return JSONStorage(config.storage.path)
        elif storage_type == "csv":
            return CSVStorage(config.storage.path)
        elif storage_type == "database":
            if not config.storage.database_url:
                raise ValueError("Database URL is required for database storage")
            return DatabaseStorage(config.storage.database_url)
        elif storage_type == "telemetry":
            if not config.storage.telemetry:
                raise ValueError("Telemetry configuration is required for telemetry storage")
            
            # Extract telemetry configuration
            loki_url = config.storage.telemetry.loki.url if config.storage.telemetry.loki.enabled else None
            prometheus_url = config.storage.telemetry.prometheus.url if config.storage.telemetry.prometheus.enabled else None
            
            return TelemetryStorageBackend(
                loki_url=loki_url,
                prometheus_url=prometheus_url,
                instance_id=config.storage.telemetry.loki.instance_id,
                job_name=config.storage.telemetry.prometheus.job_name
            )
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

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
                    
                    # For telemetry storage, also send additional metrics
                    if isinstance(self.storage, TelemetryStorageBackend):
                        await self._send_telemetry_metrics(all_intervals)

                # Wait before next processing cycle
                await asyncio.sleep(self.config.processing.interval)

            except Exception as e:
                logger.error("Error processing intervals", error=str(e))
                await asyncio.sleep(1.0)  # Brief pause before retry

    async def _send_telemetry_metrics(self, intervals: List[IntervalData]) -> None:
        """Send additional telemetry metrics for monitoring."""
        try:
            # Group intervals by game type and table for counter metrics
            game_table_counts = {}
            total_duration_by_type = {}
            
            for interval in intervals:
                key = f"{interval.game_type}:{interval.table}"
                game_table_counts[key] = game_table_counts.get(key, 0) + 1
                
                interval_type_key = f"{interval.game_type}:{interval.interval_type.value}"
                if interval_type_key not in total_duration_by_type:
                    total_duration_by_type[interval_type_key] = {"total": 0.0, "count": 0}
                total_duration_by_type[interval_type_key]["total"] += interval.duration
                total_duration_by_type[interval_type_key]["count"] += 1
            
            # Send counter metrics for intervals processed
            for key, count in game_table_counts.items():
                game_type, table = key.split(":", 1)
                self.storage.send_counter_metric(
                    metric_name="intervals_processed_total",
                    value=count,
                    game_type=game_type,
                    table=table
                )
            
            # Send gauge metrics for average durations
            for key, data in total_duration_by_type.items():
                game_type, interval_type = key.split(":", 1)
                avg_duration = data["total"] / data["count"]
                
                # Extract table from intervals (assuming all intervals have same table for this type)
                table = intervals[0].table if intervals else "unknown"
                
                self.storage.send_gauge_metric(
                    metric_name="interval_duration_avg",
                    value=avg_duration,
                    game_type=game_type,
                    table=table,
                    additional_labels={"interval_type": interval_type}
                )
            
            logger.debug("Sent telemetry metrics", 
                        counter_metrics=len(game_table_counts),
                        gauge_metrics=len(total_duration_by_type))
                        
        except Exception as e:
            logger.error("Error sending telemetry metrics", error=str(e))

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
    
    async def test_telemetry_connections(self) -> Dict[str, bool]:
        """
        Test connections to telemetry servers.
        
        Returns:
            Dictionary with connection test results
        """
        if isinstance(self.storage, TelemetryStorageBackend):
            return await self.storage.test_connections()
        else:
            return {"telemetry": False, "reason": "Not using telemetry storage"}
