"""Enhanced logging configuration with rotation and persistence."""

import logging
import logging.handlers
import sys

from pythonjsonlogger import jsonlogger

from mcpy_lens.config import get_settings


def setup_logging(
    log_level: str | None = None,
    enable_file_logging: bool = True,
    enable_rotation: bool = True,
) -> None:
    """
    Set up comprehensive logging with console and file handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to enable file logging
        enable_rotation: Whether to enable log rotation
    """
    settings = get_settings()

    # Ensure logs directory exists
    settings.create_directories()

    # Determine log level
    level = getattr(logging, (log_level or settings.log_level).upper(), logging.INFO)

    # Create custom formatter for console
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create JSON formatter for file logging
    json_formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(pathname)s %(lineno)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    if enable_file_logging:
        # Main application log file
        app_log_file = settings.logs_dir / "mcpy_lens.log"

        if enable_rotation:
            # Rotating file handler (10MB max, keep 5 backups)
            file_handler = logging.handlers.RotatingFileHandler(
                filename=app_log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
        else:
            # Regular file handler
            file_handler = logging.FileHandler(filename=app_log_file, encoding="utf-8")

        file_handler.setLevel(level)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)

        # Error-specific log file
        error_log_file = settings.logs_dir / "errors.log"
        error_handler = logging.FileHandler(filename=error_log_file, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        root_logger.addHandler(error_handler)

        # Access log for FastAPI (separate logger)
        access_logger = logging.getLogger("uvicorn.access")
        access_log_file = settings.logs_dir / "access.log"

        if enable_rotation:
            access_handler = logging.handlers.RotatingFileHandler(
                filename=access_log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=3,
                encoding="utf-8",
            )
        else:
            access_handler = logging.FileHandler(
                filename=access_log_file, encoding="utf-8"
            )

        access_handler.setFormatter(json_formatter)
        access_logger.addHandler(access_handler)

    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("fastapi").setLevel(level)
    logging.getLogger("mcpy_lens").setLevel(level)

    # Suppress noisy loggers in production
    if level >= logging.INFO:
        logging.getLogger("watchfiles").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.info(
        f"Logging configured: level={logging.getLevelName(level)}, file_logging={enable_file_logging}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)
