"""
Main entry point for Studio Round Time Monitor.

Provides command-line interface and standalone execution capability
for the time monitoring system.
"""

import asyncio
import argparse
import signal
import sys
from pathlib import Path
from typing import Optional
import structlog

from .core.time_monitor import TimeMonitor
from .utils.config import load_config, create_default_config
from .utils.logger import setup_logging

logger = structlog.get_logger(__name__)

class MonitorApplication:
    """Main application class for the time monitor."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the monitor application.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = None
        self.time_monitor = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize the application."""
        try:
            # Load configuration
            if self.config_path and Path(self.config_path).exists():
                self.config = load_config(self.config_path)
            else:
                logger.warning("Config file not found, creating default configuration")
                if self.config_path:
                    self.config = create_default_config(self.config_path)
                else:
                    self.config = load_config()  # Use default path

            # Setup logging
            setup_logging(
                log_level="INFO",
                log_file=f"./logs/roundtime_monitor_{self.config.storage.type}.log",
                log_format="json"
            )

            # Initialize time monitor
            self.time_monitor = TimeMonitor(self.config)

            # Setup signal handlers
            self._setup_signal_handlers()

            logger.info("Application initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize application", error=str(e))
            raise

    async def run(self) -> None:
        """Run the monitor application."""
        try:
            await self.initialize()

            # Start the time monitor
            await self.time_monitor.start()

            logger.info("Time monitor started, waiting for shutdown signal...")

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Application error", error=str(e))
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the application."""
        try:
            logger.info("Shutting down application...")

            if self.time_monitor:
                await self.time_monitor.stop()

            logger.info("Application shutdown complete")

        except Exception as e:
            logger.error("Error during shutdown", error=str(e))

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal", signal=signum)
            self._shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def get_status(self) -> dict:
        """Get application status."""
        if not self.time_monitor:
            return {"status": "not_initialized"}

        return {
            "status": "running" if self.time_monitor._running else "stopped",
            "config": self.config.to_dict(),
            "health": self.time_monitor.get_health_status()
        }

def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Studio Round Time Monitor - Time monitoring system for SDP games"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )

    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default configuration file and exit"
    )

    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration file and exit"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level"
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show application status and exit"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Studio Round Time Monitor 1.0.0"
    )

    return parser

async def main() -> None:
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Handle configuration creation
    if args.create_config:
        config_path = args.config or "config/monitor_config.yaml"
        create_default_config(config_path)
        print(f"Default configuration created at: {config_path}")
        return

    # Handle configuration validation
    if args.validate_config:
        config_path = args.config or "config/monitor_config.yaml"
        try:
            config = load_config(config_path)
            print(f"Configuration is valid: {config_path}")
            print(f"Configuration: {config.to_dict()}")
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            sys.exit(1)
        return

    # Handle status request
    if args.status:
        try:
            app = MonitorApplication(args.config)
            await app.initialize()
            status = app.get_status()
            print(f"Application Status: {status}")
        except Exception as e:
            print(f"Failed to get status: {e}")
            sys.exit(1)
        return

    # Setup logging based on arguments
    setup_logging(
        log_level=args.log_level,
        log_file=args.log_file,
        log_format="json"
    )

    # Run the application
    app = MonitorApplication(args.config)
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)
