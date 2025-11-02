"""
Logging configuration for the application.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger

from src.utils.constants import (
    LOG_CONTEXT_CAMPAIGN_ID,
    LOG_CONTEXT_GENERATION_TIME,
    LOG_CONTEXT_MODEL_USED,
    LOG_CONTEXT_REQUEST_ID,
    LOG_CONTEXT_TOKENS_USED,
    LOG_CONTEXT_USER_ID,
)


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
        log_record.setdefault("module", record.module)
        log_record.setdefault("function", record.funcName)
        log_record.setdefault("line", record.lineno)
        log_record.setdefault("timestamp", self.formatTime(record, self.datefmt))

        # Add process and thread info
        if not log_record.get("process"):
            log_record["process"] = record.process
        if not log_record.get("thread"):
            log_record["thread"] = record.thread


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: str | None = None,
) -> None:
    """Setup application logging."""

    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Setup formatters
    if format_type == "json":
        formatter = JSONFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        )
    else:
        formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

    # Setup structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if log_level <= logging.DEBUG else logging.WARNING
    )
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info(
        "Logging configured",
        extra={
            "level": level,
            "format": format_type,
            "file": log_file,
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context: Any,
) -> None:
    """Log message with additional context."""
    extra = {}

    # Add standard context fields
    if LOG_CONTEXT_REQUEST_ID in context:
        extra["request_id"] = context[LOG_CONTEXT_REQUEST_ID]
    if LOG_CONTEXT_USER_ID in context:
        extra["user_id"] = context[LOG_CONTEXT_USER_ID]
    if LOG_CONTEXT_CAMPAIGN_ID in context:
        extra["campaign_id"] = context[LOG_CONTEXT_CAMPAIGN_ID]
    if LOG_CONTEXT_GENERATION_TIME in context:
        extra["generation_time_ms"] = context[LOG_CONTEXT_GENERATION_TIME]
    if LOG_CONTEXT_TOKENS_USED in context:
        extra["tokens_used"] = context[LOG_CONTEXT_TOKENS_USED]
    if LOG_CONTEXT_MODEL_USED in context:
        extra["model_used"] = context[LOG_CONTEXT_MODEL_USED]

    # Add custom context
    for key, value in context.items():
        if key not in extra:
            extra[key] = value

    getattr(logger, level.lower())(message, extra=extra)


class RequestLogger:
    """Logger for HTTP requests."""

    def __init__(self, logger_name: str = "request"):
        self.logger = get_logger(logger_name)

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Log HTTP request."""
        context = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }

        if request_id:
            context[LOG_CONTEXT_REQUEST_ID] = request_id
        if user_id:
            context[LOG_CONTEXT_USER_ID] = user_id

        level = "INFO" if status_code < 400 else "WARNING"
        log_with_context(
            self.logger,
            level,
            f"{method} {path} - {status_code}",
            **context
        )


class CampaignLogger:
    """Logger for campaign generation events."""

    def __init__(self, logger_name: str = "campaign"):
        self.logger = get_logger(logger_name)

    def log_generation_start(
        self,
        campaign_description: str,
        request_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Log campaign generation start."""
        context = {
            "campaign_description": campaign_description,
            "description_length": len(campaign_description),
        }

        if request_id:
            context[LOG_CONTEXT_REQUEST_ID] = request_id
        if user_id:
            context[LOG_CONTEXT_USER_ID] = user_id

        log_with_context(
            self.logger,
            "INFO",
            "Campaign generation started",
            **context
        )

    def log_generation_success(
        self,
        campaign_id: str,
        generation_time_ms: float,
        tokens_used: int,
        model_used: str,
        node_count: int,
        request_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Log successful campaign generation."""
        context = {
            LOG_CONTEXT_CAMPAIGN_ID: campaign_id,
            LOG_CONTEXT_GENERATION_TIME: generation_time_ms,
            LOG_CONTEXT_TOKENS_USED: tokens_used,
            LOG_CONTEXT_MODEL_USED: model_used,
            "node_count": node_count,
        }

        if request_id:
            context[LOG_CONTEXT_REQUEST_ID] = request_id
        if user_id:
            context[LOG_CONTEXT_USER_ID] = user_id

        log_with_context(
            self.logger,
            "INFO",
            "Campaign generation completed successfully",
            **context
        )

    def log_generation_error(
        self,
        error: str,
        error_code: str | None = None,
        generation_time_ms: float | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Log campaign generation error."""
        context = {"error": error}

        if error_code:
            context["error_code"] = error_code
        if generation_time_ms is not None:
            context[LOG_CONTEXT_GENERATION_TIME] = generation_time_ms
        if request_id:
            context[LOG_CONTEXT_REQUEST_ID] = request_id
        if user_id:
            context[LOG_CONTEXT_USER_ID] = user_id

        log_with_context(
            self.logger,
            "ERROR",
            "Campaign generation failed",
            **context
        )