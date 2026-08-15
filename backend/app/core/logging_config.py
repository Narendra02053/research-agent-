"""
logging_config.py
Configures structured, production-grade JSON logging with correlation IDs,
latency tracking, error categorization, and rotating file handlers.
"""

import json
import logging
import sys
import time
import os
import traceback
import uuid
from typing import Callable, Optional
from functools import wraps
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter.
    Produces machine-readable log entries with consistent schema.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            if isinstance(record.exc_info, bool):
                record.exc_info = sys.exc_info()
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else None,
            }

        extra_keys = [
            "request_id", "job_id", "trace_id",
            "research_id", "session_id",
            "event", "latency_ms",
            "provider", "model", "tokens_used",
            "status", "error_category",
        ]
        for key in extra_keys:
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def configure_logging(log_dir: Optional[str] = None) -> None:
    """
    Set up structured JSON logging with rotating file and console handlers.
    Should be called once at application startup (in main.py).

    Args:
        log_dir: Directory for log files. Defaults to 'logs/' in project root.
    """
    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    json_formatter = JSONFormatter()
    text_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)

    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=100 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(json_formatter)

    error_file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "error.log"),
        maxBytes=100 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(json_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Structured JSON logging initialized", extra={
        "event": "logging_initialized",
        "log_dir": log_dir,
    })


class LoggerMixin:
    """
    Mixin that provides a structured logger to any class.
    Usage: class MyClass(LoggerMixin): ...
    """

    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_structured_logger"):
            self._structured_logger = logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._structured_logger

    def log_event(self, event: str, **extra: object) -> None:
        self.logger.info(f"Event: {event}", extra={"event": event, **extra})

    def log_error(self, event: str, error: Exception, **extra: object) -> None:
        extra["error_category"] = type(error).__name__
        extra["event"] = event
        self.logger.error(f"Error: {event} — {error}", extra=extra, exc_info=True)


def generate_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def generate_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


def generate_research_id() -> str:
    return f"res_{uuid.uuid4().hex[:12]}"


def log_execution_time(logger: logging.Logger, event: str) -> Callable:
    """
    Context manager-style decorator for timing functions.
    Usage:
        @log_execution_time(logger, "Reranking step")
        def rerank(...): ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> object:
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(f"[OK] {event}", extra={
                    "event": event,
                    "latency_ms": round(elapsed, 2),
                    "status": "success",
                })
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(f"[FAIL] {event}", extra={
                    "event": event,
                    "latency_ms": round(elapsed, 2),
                    "status": "failed",
                    "error_category": type(e).__name__,
                })
                raise
        return wrapper
    return decorator


def async_log_execution_time(logger: logging.Logger, event: str) -> Callable:
    """
    Async version of log_execution_time.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args: object, **kwargs: object) -> object:
            start = time.perf_counter()
            try:
                result = await fn(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(f"[OK] {event}", extra={
                    "event": event,
                    "latency_ms": round(elapsed, 2),
                    "status": "success",
                })
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(f"[FAIL] {event}", extra={
                    "event": event,
                    "latency_ms": round(elapsed, 2),
                    "status": "failed",
                    "error_category": type(e).__name__,
                })
                raise
        return wrapper
    return decorator


def timed(label: str) -> Callable:
    """
    Legacy compatibility decorator. Uses JSON logging internally.
    Usage: @timed("Reranking step")
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> object:
            logger = logging.getLogger(fn.__module__)
            start = time.perf_counter()
            logger.info(f"[START] {label}", extra={"event": label, "status": "start"})
            try:
                result = fn(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(f"[DONE] {label}", extra={
                    "event": label,
                    "latency_ms": round(elapsed * 1000, 2),
                    "status": "success",
                })
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"[FAIL] {label}", extra={
                    "event": label,
                    "latency_ms": round(elapsed * 1000, 2),
                    "status": "failed",
                    "error_category": type(e).__name__,
                })
                raise
        return wrapper
    return decorator


def async_timed(label: str) -> Callable:
    """
    Legacy async compatibility decorator.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args: object, **kwargs: object) -> object:
            logger = logging.getLogger(fn.__module__)
            start = time.perf_counter()
            logger.info(f"[START] {label}", extra={"event": label, "status": "start"})
            try:
                result = await fn(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(f"[DONE] {label}", extra={
                    "event": label,
                    "latency_ms": round(elapsed * 1000, 2),
                    "status": "success",
                })
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"[FAIL] {label}", extra={
                    "event": label,
                    "latency_ms": round(elapsed * 1000, 2),
                    "status": "failed",
                    "error_category": type(e).__name__,
                })
                raise
        return wrapper
    return decorator
