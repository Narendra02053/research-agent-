"""
logging_config.py
Configures structured, production-grade logging for the AI Deep Research Agent.
Includes request timing, agent execution timing, and error tracking.
"""

import logging
import sys
import time
from typing import Callable
from functools import wraps

def configure_logging():
    """
    Set up structured logging with timestamps, log levels, and module names.
    Should be called once at application startup (in main.py).
    """
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Suppress noisy third-party logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Structured logging initialized.")


def timed(label: str):
    """
    Decorator factory to log execution time of any function.
    Usage: @timed("Reranking step")
    """
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(fn.__module__)
            start = time.perf_counter()
            logger.info(f"[START] {label}")
            try:
                result = fn(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(f"[DONE]  {label} completed in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"[FAIL]  {label} failed after {elapsed:.3f}s — {str(e)}")
                raise
        return wrapper
    return decorator


def async_timed(label: str):
    """
    Async version of the @timed decorator.
    """
    def decorator(fn: Callable):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(fn.__module__)
            start = time.perf_counter()
            logger.info(f"[START] {label}")
            try:
                result = await fn(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(f"[DONE]  {label} completed in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"[FAIL]  {label} failed after {elapsed:.3f}s — {str(e)}")
                raise
        return wrapper
    return decorator
