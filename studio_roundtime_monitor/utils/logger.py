"""
Logging configuration for Studio Round Time Monitor.

Provides structured logging setup with configurable output formats
and levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import structlog
from structlog.stdlib import LoggerFactory

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "json",
    enable_console: bool = True
) -> None:
    """
    Setup structured logging for the monitoring system.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_format: Log format ("json" or "console")
        enable_console: Enable console logging
    """
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))

        # Add file handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    # Disable console logging if requested
    if not enable_console:
        # Remove console handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                root_logger.removeHandler(handler)

    logger = structlog.get_logger(__name__)
    logger.info("Logging configured",
               level=log_level,
               file=log_file,
               format=log_format,
               console=enable_console)

def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)

class LogContext:
    """
    Context manager for adding structured logging context.

    Usage:
        with LogContext(table="PRD", round_id="123"):
            logger.info("Processing round")
    """

    def __init__(self, **context):
        """
        Initialize log context.

        Args:
            **context: Context variables to add to all log messages
        """
        self.context = context
        self.logger = structlog.get_logger()

    def __enter__(self):
        """Enter context."""
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        pass

def log_function_call(func_name: str, **kwargs):
    """
    Decorator to log function calls with parameters.

    Args:
        func_name: Function name to log
        **kwargs: Additional context to include
    """
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            logger = structlog.get_logger()

            # Combine context
            context = {
                "function": func_name,
                "args_count": len(args),
                **kwargs
            }

            with LogContext(**context):
                logger.info("Function called",
                           args=args if len(args) <= 5 else f"{len(args)} arguments",
                           kwargs=func_kwargs)

                try:
                    result = func(*args, **func_kwargs)
                    logger.info("Function completed successfully")
                    return result
                except Exception as e:
                    logger.error("Function failed", error=str(e), exc_info=True)
                    raise

        return wrapper
    return decorator

def log_performance(operation: str):
    """
    Decorator to log performance metrics.

    Args:
        operation: Operation name to log
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            import time
            logger = structlog.get_logger()

            start_time = time.time()
            with LogContext(operation=operation):
                logger.info("Operation started")

                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.info("Operation completed", duration=duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error("Operation failed", duration=duration, error=str(e))
                    raise

        def sync_wrapper(*args, **kwargs):
            import time
            logger = structlog.get_logger()

            start_time = time.time()
            with LogContext(operation=operation):
                logger.info("Operation started")

                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.info("Operation completed", duration=duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error("Operation failed", duration=duration, error=str(e))
                    raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

# Configure default logging
setup_logging()
