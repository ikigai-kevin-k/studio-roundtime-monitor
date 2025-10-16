"""
Event system for Studio Round Time Monitor.

Provides a publish/subscribe system for time monitoring events that allows
the main game modules to publish timing events without direct coupling.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

class EventType(Enum):
    """Types of events that can be monitored."""

    # TableAPI events
    TABLEAPI_START = "tableapi_start"
    TABLEAPI_BETSTOP = "tableapi_betstop"
    TABLEAPI_DEAL = "tableapi_deal"
    TABLEAPI_FINISH = "tableapi_finish"

    # Roulette device events
    ROULETTE_X2 = "roulette_x2"  # Ball launch
    ROULETTE_X3 = "roulette_x3"  # Ball landing
    ROULETTE_X4 = "roulette_x4"  # Detection
    ROULETTE_X5 = "roulette_x5"  # Result announcement

    # Sicbo shaker events
    SICBO_SHAKER_START = "sicbo_shaker_start"
    SICBO_SHAKER_STOP = "sicbo_shaker_stop"
    SICBO_SHAKER_S0 = "sicbo_shaker_s0"

    # Sicbo IDP events
    SICBO_IDP_SEND = "sicbo_idp_send"
    SICBO_IDP_RECEIVE = "sicbo_idp_receive"

    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    ROUND_START = "round_start"
    ROUND_END = "round_end"

@dataclass
class GameEvent:
    """Represents a game event with timing information."""

    event_type: EventType
    timestamp: float
    game_type: str  # 'roulette', 'sicbo', 'baccarat'
    table: str
    round_id: str
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate event data after initialization."""
        if not self.timestamp:
            self.timestamp = time.time()

        if not self.game_type:
            raise ValueError("game_type is required")

        if not self.table:
            raise ValueError("table is required")

        if not self.round_id:
            raise ValueError("round_id is required")

class EventSystem:
    """
    Event publish/subscribe system for time monitoring.

    Allows game modules to publish events without direct coupling to monitors.
    Monitors can subscribe to specific event types and receive notifications.
    """

    def __init__(self):
        """Initialize the event system."""
        self._subscribers: Dict[EventType, Set[Callable[[GameEvent], None]]] = {}
        self._async_subscribers: Dict[EventType, Set[Callable[[GameEvent], None]]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: EventType, callback: Callable[[GameEvent], None]) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: The type of events to subscribe to
            callback: Function to call when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()

        self._subscribers[event_type].add(callback)
        logger.info("Subscribed to event type", event_type=event_type.value)

    def subscribe_async(self, event_type: EventType, callback: Callable[[GameEvent], None]) -> None:
        """
        Subscribe to events of a specific type with async callback.

        Args:
            event_type: The type of events to subscribe to
            callback: Async function to call when event is published
        """
        if event_type not in self._async_subscribers:
            self._async_subscribers[event_type] = set()

        self._async_subscribers[event_type].add(callback)
        logger.info("Subscribed to async event type", event_type=event_type.value)

    def unsubscribe(self, event_type: EventType, callback: Callable[[GameEvent], None]) -> None:
        """
        Unsubscribe from events of a specific type.

        Args:
            event_type: The type of events to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(callback)

        if event_type in self._async_subscribers:
            self._async_subscribers[event_type].discard(callback)

        logger.info("Unsubscribed from event type", event_type=event_type.value)

    def publish(self, event: GameEvent) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        logger.debug("Publishing event",
                    event_type=event.event_type.value,
                    game_type=event.game_type,
                    table=event.table,
                    round_id=event.round_id)

        # Notify synchronous subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error("Error in event callback",
                               event_type=event.event_type.value,
                               error=str(e))

        # Queue event for asynchronous subscribers
        if event.event_type in self._async_subscribers:
            try:
                self._event_queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event queue is full, dropping event",
                             event_type=event.event_type.value)

    def publish_simple(self,
                      event_type: EventType,
                      game_type: str,
                      table: str,
                      round_id: str,
                      **data) -> None:
        """
        Publish an event with simplified parameters.

        Args:
            event_type: Type of the event
            game_type: Type of game ('roulette', 'sicbo', etc.)
            table: Table identifier
            round_id: Round identifier
            **data: Additional event data
        """
        event = GameEvent(
            event_type=event_type,
            timestamp=time.time(),
            game_type=game_type,
            table=table,
            round_id=round_id,
            data=data
        )
        self.publish(event)

    async def start(self) -> None:
        """Start the async event processing loop."""
        if self._running:
            logger.warning("Event system is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._process_events())
        logger.info("Event system started")

    async def stop(self) -> None:
        """Stop the async event processing loop."""
        if not self._running:
            logger.warning("Event system is not running")
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Event system stopped")

    async def _process_events(self) -> None:
        """Process events from the queue for async subscribers."""
        while self._running:
            try:
                # Wait for event with timeout to allow checking _running flag
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)

                if event.event_type in self._async_subscribers:
                    for callback in self._async_subscribers[event.event_type]:
                        try:
                            await callback(event)
                        except Exception as e:
                            logger.error("Error in async event callback",
                                       event_type=event.event_type.value,
                                       error=str(e))

            except asyncio.TimeoutError:
                # Timeout is expected, continue loop
                continue
            except Exception as e:
                logger.error("Error processing event", error=str(e))

    def get_subscriber_count(self, event_type: EventType) -> int:
        """
        Get the number of subscribers for an event type.

        Args:
            event_type: The event type to check

        Returns:
            Number of subscribers
        """
        sync_count = len(self._subscribers.get(event_type, set()))
        async_count = len(self._async_subscribers.get(event_type, set()))
        return sync_count + async_count

    def get_all_event_types(self) -> List[EventType]:
        """Get all event types that have subscribers."""
        all_types = set()
        all_types.update(self._subscribers.keys())
        all_types.update(self._async_subscribers.keys())
        return list(all_types)
