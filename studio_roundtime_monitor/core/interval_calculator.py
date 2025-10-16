"""
Interval calculator for Studio Round Time Monitor.

Calculates time intervals between events and provides statistical analysis
of timing patterns.
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

class IntervalType(Enum):
    """Types of intervals that can be calculated."""

    # TableAPI intervals
    START_TO_BETSTOP = "start-to-betstop"
    BETSTOP_TO_DEAL = "betstop-to-deal"
    DEAL_TO_FINISH = "deal-to-finish"
    FINISH_TO_START = "finish-to-start"

    # Roulette device intervals
    X2_TO_X3 = "*X;2-to-*X;3"  # Ball launch to landing
    X3_TO_X4 = "*X;3-to-*X;4"  # Landing to detection
    X4_TO_X5 = "*X;4-to-*X;5"  # Detection to result
    X5_TO_X2 = "*X;5-to-*X;2"  # Result to next launch

    # Sicbo shaker intervals
    SHAKER_STOP_TO_SHAKE = "shakerStop-to-shakerShake"
    SHAKER_SHAKE_TO_STOP = "shakerShake-to-shakerStop"

    # Sicbo IDP intervals
    IDP_SEND_TO_RECEIVE = "sendDetect-to-receiveResult"
    IDP_RECEIVE_TO_SEND = "receiveResult-to-sendDetect"

@dataclass
class IntervalData:
    """Represents calculated interval data."""

    interval_type: IntervalType
    duration: float  # Duration in seconds
    timestamp: float
    game_type: str
    table: str
    round_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "interval_type": self.interval_type.value,
            "duration": self.duration,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "game_type": self.game_type,
            "table": self.table,
            "round_id": self.round_id,
            "metadata": self.metadata
        }

@dataclass
class IntervalStatistics:
    """Statistical data for a specific interval type."""

    interval_type: IntervalType
    count: int
    min_duration: float
    max_duration: float
    avg_duration: float
    median_duration: float
    std_deviation: float
    recent_intervals: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "interval_type": self.interval_type.value,
            "count": self.count,
            "min_duration": self.min_duration,
            "max_duration": self.max_duration,
            "avg_duration": self.avg_duration,
            "median_duration": self.median_duration,
            "std_deviation": self.std_deviation,
            "recent_intervals": self.recent_intervals
        }

class IntervalCalculator:
    """
    Calculates time intervals between events and maintains statistics.

    Tracks the timing of events and calculates intervals between them,
    providing statistical analysis and anomaly detection.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize the interval calculator.

        Args:
            max_history: Maximum number of intervals to keep in history
        """
        self.max_history = max_history
        self._event_history: Dict[Tuple[str, str, str], Dict[str, float]] = {}
        self._interval_history: Dict[IntervalType, List[IntervalData]] = {}
        self._statistics: Dict[IntervalType, IntervalStatistics] = {}

        # Initialize interval history for all types
        for interval_type in IntervalType:
            self._interval_history[interval_type] = []
            self._statistics[interval_type] = IntervalStatistics(
                interval_type=interval_type,
                count=0,
                min_duration=float('inf'),
                max_duration=0.0,
                avg_duration=0.0,
                median_duration=0.0,
                std_deviation=0.0
            )

    def record_event(self,
                    event_type: str,
                    game_type: str,
                    table: str,
                    round_id: str,
                    timestamp: Optional[float] = None) -> List[IntervalData]:
        """
        Record an event and calculate any resulting intervals.

        Args:
            event_type: Type of the event
            game_type: Type of game
            table: Table identifier
            round_id: Round identifier
            timestamp: Event timestamp (defaults to current time)

        Returns:
            List of newly calculated intervals
        """
        if timestamp is None:
            timestamp = time.time()

        key = (game_type, table, round_id)
        new_intervals = []

        # Store the event timestamp
        if key not in self._event_history:
            self._event_history[key] = {}

        self._event_history[key][event_type] = timestamp

        # Calculate intervals based on event type
        if event_type == "tableapi_finish":
            intervals = self._calculate_tableapi_intervals(key, timestamp)
            new_intervals.extend(intervals)
        elif event_type == "roulette_x5":
            intervals = self._calculate_roulette_intervals(key, timestamp)
            new_intervals.extend(intervals)
        elif event_type == "sicbo_idp_receive":
            intervals = self._calculate_sicbo_intervals(key, timestamp)
            new_intervals.extend(intervals)

        # Update statistics for new intervals
        for interval in new_intervals:
            self._update_statistics(interval)

        # Clean up old history to prevent memory leaks
        self._cleanup_history()

        return new_intervals

    def _calculate_tableapi_intervals(self,
                                    key: Tuple[str, str, str],
                                    timestamp: float) -> List[IntervalData]:
        """Calculate TableAPI intervals."""
        game_type, table, round_id = key
        events = self._event_history[key]
        intervals = []

        # Calculate start-to-betstop interval
        if "tableapi_start" in events and "tableapi_betstop" in events:
            duration = events["tableapi_betstop"] - events["tableapi_start"]
            interval = IntervalData(
                interval_type=IntervalType.START_TO_BETSTOP,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        # Calculate betstop-to-deal interval
        if "tableapi_betstop" in events and "tableapi_deal" in events:
            duration = events["tableapi_deal"] - events["tableapi_betstop"]
            interval = IntervalData(
                interval_type=IntervalType.BETSTOP_TO_DEAL,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        # Calculate deal-to-finish interval
        if "tableapi_deal" in events and "tableapi_finish" in events:
            duration = events["tableapi_finish"] - events["tableapi_deal"]
            interval = IntervalData(
                interval_type=IntervalType.DEAL_TO_FINISH,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        return intervals

    def _calculate_roulette_intervals(self,
                                    key: Tuple[str, str, str],
                                    timestamp: float) -> List[IntervalData]:
        """Calculate Roulette device intervals."""
        game_type, table, round_id = key
        events = self._event_history[key]
        intervals = []

        # Calculate *X;2-to-*X;3 interval (ball launch to landing)
        if "roulette_x2" in events and "roulette_x3" in events:
            duration = events["roulette_x3"] - events["roulette_x2"]
            interval = IntervalData(
                interval_type=IntervalType.X2_TO_X3,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        # Calculate *X;3-to-*X;4 interval (landing to detection)
        if "roulette_x3" in events and "roulette_x4" in events:
            duration = events["roulette_x4"] - events["roulette_x3"]
            interval = IntervalData(
                interval_type=IntervalType.X3_TO_X4,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        # Calculate *X;4-to-*X;5 interval (detection to result)
        if "roulette_x4" in events and "roulette_x5" in events:
            duration = events["roulette_x5"] - events["roulette_x4"]
            interval = IntervalData(
                interval_type=IntervalType.X4_TO_X5,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        return intervals

    def _calculate_sicbo_intervals(self,
                                 key: Tuple[str, str, str],
                                 timestamp: float) -> List[IntervalData]:
        """Calculate Sicbo device intervals."""
        game_type, table, round_id = key
        events = self._event_history[key]
        intervals = []

        # Calculate shaker stop-to-shake interval
        if "sicbo_shaker_stop" in events and "sicbo_shaker_start" in events:
            duration = events["sicbo_shaker_start"] - events["sicbo_shaker_stop"]
            interval = IntervalData(
                interval_type=IntervalType.SHAKER_STOP_TO_SHAKE,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        # Calculate shaker shake-to-stop interval
        if "sicbo_shaker_start" in events and "sicbo_shaker_stop" in events:
            duration = events["sicbo_shaker_stop"] - events["sicbo_shaker_start"]
            interval = IntervalData(
                interval_type=IntervalType.SHAKER_SHAKE_TO_STOP,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        # Calculate IDP send-to-receive interval
        if "sicbo_idp_send" in events and "sicbo_idp_receive" in events:
            duration = events["sicbo_idp_receive"] - events["sicbo_idp_send"]
            interval = IntervalData(
                interval_type=IntervalType.IDP_SEND_TO_RECEIVE,
                duration=duration,
                timestamp=timestamp,
                game_type=game_type,
                table=table,
                round_id=round_id
            )
            intervals.append(interval)

        return intervals

    def _update_statistics(self, interval: IntervalData) -> None:
        """Update statistics for an interval type."""
        interval_type = interval.interval_type
        stats = self._statistics[interval_type]

        # Add to history
        self._interval_history[interval_type].append(interval)

        # Update basic statistics
        stats.count += 1
        stats.min_duration = min(stats.min_duration, interval.duration)
        stats.max_duration = max(stats.max_duration, interval.duration)

        # Update recent intervals (keep last 10)
        stats.recent_intervals.append(interval.duration)
        if len(stats.recent_intervals) > 10:
            stats.recent_intervals.pop(0)

        # Calculate average and median
        all_durations = [i.duration for i in self._interval_history[interval_type]]
        stats.avg_duration = sum(all_durations) / len(all_durations)

        sorted_durations = sorted(all_durations)
        n = len(sorted_durations)
        if n % 2 == 0:
            stats.median_duration = (sorted_durations[n//2-1] + sorted_durations[n//2]) / 2
        else:
            stats.median_duration = sorted_durations[n//2]

        # Calculate standard deviation
        if len(all_durations) > 1:
            variance = sum((x - stats.avg_duration) ** 2 for x in all_durations) / (len(all_durations) - 1)
            stats.std_deviation = variance ** 0.5
        else:
            stats.std_deviation = 0.0

    def _cleanup_history(self) -> None:
        """Clean up old history to prevent memory leaks."""
        for interval_type, intervals in self._interval_history.items():
            if len(intervals) > self.max_history:
                # Keep only the most recent intervals
                self._interval_history[interval_type] = intervals[-self.max_history:]

    def get_statistics(self, interval_type: IntervalType) -> IntervalStatistics:
        """Get statistics for a specific interval type."""
        return self._statistics[interval_type]

    def get_all_statistics(self) -> Dict[IntervalType, IntervalStatistics]:
        """Get statistics for all interval types."""
        return self._statistics.copy()

    def get_intervals(self,
                     interval_type: IntervalType,
                     limit: Optional[int] = None) -> List[IntervalData]:
        """Get recent intervals for a specific type."""
        intervals = self._interval_history[interval_type]
        if limit is not None:
            return intervals[-limit:]
        return intervals.copy()

    def detect_anomalies(self,
                        interval_type: IntervalType,
                        threshold_multiplier: float = 2.0) -> List[IntervalData]:
        """
        Detect anomalous intervals based on statistical thresholds.

        Args:
            interval_type: Type of interval to check
            threshold_multiplier: Multiplier for standard deviation threshold

        Returns:
            List of intervals considered anomalous
        """
        stats = self._statistics[interval_type]
        if stats.count < 3:  # Need at least 3 data points
            return []

        threshold = stats.std_deviation * threshold_multiplier
        upper_bound = stats.avg_duration + threshold
        lower_bound = stats.avg_duration - threshold

        anomalous = []
        for interval in self._interval_history[interval_type]:
            if interval.duration > upper_bound or interval.duration < lower_bound:
                anomalous.append(interval)

        return anomalous

    def clear_history(self, interval_type: Optional[IntervalType] = None) -> None:
        """Clear history for a specific interval type or all types."""
        if interval_type is None:
            # Clear all history
            for it in IntervalType:
                self._interval_history[it] = []
                self._statistics[it] = IntervalStatistics(
                    interval_type=it,
                    count=0,
                    min_duration=float('inf'),
                    max_duration=0.0,
                    avg_duration=0.0,
                    median_duration=0.0,
                    std_deviation=0.0
                )
        else:
            # Clear specific type
            self._interval_history[interval_type] = []
            self._statistics[interval_type] = IntervalStatistics(
                interval_type=interval_type,
                count=0,
                min_duration=float('inf'),
                max_duration=0.0,
                avg_duration=0.0,
                median_duration=0.0,
                std_deviation=0.0
            )
