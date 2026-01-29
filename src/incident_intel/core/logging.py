"""Structured logging configuration using structlog.

Provides JSON logging for production and pretty-printed logs for development.
Automatically adds request_id correlation to all logs.

Security & Privacy Strategy:
    Production (LOG_LEVEL=INFO or higher):
        - No user-generated content (titles, descriptions) in logs
        - Only system identifiers (ticket_id, service_id, request_id)
        - Error types only (no database schema details like constraint names)
        - Logs safe to export to third-party aggregators (Datadog, Splunk)

    Development (LOG_LEVEL=DEBUG):
        - Full context including user content and detailed errors
        - Uses test/synthetic data only (no real PII)
        - DEBUG logs are filtered out in production

Correlation Strategy:
    - request_id: Trace all operations within a single HTTP request
    - ticket_id: Look up full ticket details in database when needed
    - service_id: Identify patterns across services

Performance:
    - Early filtering at structlog level (log_level) prevents unnecessary processing
    - CallsiteParameterAdder adds file/line info (acceptable overhead for typical APIs)
    - Cached logger instances avoid repeated configuration lookups
"""

import logging
import os
import sys

import structlog


def is_development() -> bool:
    """Check if running in development mode.

    Returns:
        True if in development (interactive terminal), False otherwise.
    """
    return sys.stderr.isatty()


def configure_logging() -> None:
    """Configure structlog for the application.

    Sets up:
    - JSON output for production (machine-readable)
    - Pretty colored output for development (human-readable)
    - Automatic timestamp and log level addition
    - Request ID correlation (added by middleware)
    - Captures stdlib logs (uvicorn, sqlalchemy) with same formatting
    """
    # Determine output format based on environment
    dev_mode = is_development()

    # Get log level from environment, default to INFO
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Define processors shared by both structlog and stdlib logs
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # Includes request_id
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        # Where logging was called (file, line)
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # Final rendering processors (applied last)
    rendering_processors = [
        # Renders the call stack when explicitly requested with stack_info=True
        structlog.processors.StackInfoRenderer(),
        # Formats exception tracebacks for both dev and prod
        structlog.processors.format_exc_info,
        # Final rendering: Pretty for dev, JSON for prod
        structlog.dev.ConsoleRenderer() if dev_mode else structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Create formatter that applies structlog processors to stdlib logs
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            *shared_processors,
            *rendering_processors,
        ],
    )

    # Configure stdlib logging with handler + formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    # Configure Python's underlying logging system
    logging.basicConfig(handlers=[handler], level=log_level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger.

    Args:
        name: Optional logger name (typically __name__ of the module).
              If None, returns the root logger.

    Returns:
        Configured structlog logger instance.

    Note:
        Returns BoundLoggerLazyProxy at runtime, but annotated as BoundLogger
        since it implements the same interface (structural typing).

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_action", user_id=123, action="login")
    """
    return structlog.get_logger(name)
