"""
Studio Round Time Monitor

A comprehensive time monitoring module for SDP game systems that tracks
various timing intervals for TableAPI calls, Roulette device operations,
and Sicbo device operations.

Key Features:
- Non-intrusive monitoring via event publish/subscribe system
- Support for multiple game types (Roulette, Sicbo)
- Comprehensive coverage of timing metrics
- Flexible data storage options
- Real-time analysis and anomaly detection
"""

__version__ = "1.0.0"
__author__ = "Studio Development Team"
__email__ = "dev@studio.com"

from .core.time_monitor import TimeMonitor
from .core.event_system import EventSystem, GameEvent
from .monitors.tableapi_monitor import TableAPIMonitor
from .monitors.roulette_monitor import RouletteMonitor
from .monitors.sicbo_monitor import SicboMonitor

__all__ = [
    "TimeMonitor",
    "EventSystem",
    "GameEvent",
    "TableAPIMonitor",
    "RouletteMonitor",
    "SicboMonitor",
]
