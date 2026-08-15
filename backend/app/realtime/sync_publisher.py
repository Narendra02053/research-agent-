"""
sync_publisher.py
Thread-safe Redis pub/sub for Celery workers and other sync contexts.
Avoids asyncio event-loop issues when publishing from background tasks.
"""

import os
import time
import logging
from typing import Optional

import redis

from app.realtime.event_models import StreamEvent

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        _redis_client = redis.Redis(
            host=host, port=port, decode_responses=True, socket_connect_timeout=2
        )
    return _redis_client


def publish_event_sync(job_id: str, event_type: str, data: dict) -> None:
    event = StreamEvent(
        event_type=event_type,
        job_id=job_id,
        data=data,
        timestamp=time.time(),
    )
    channel = f"stream:{job_id}"
    try:
        _get_redis().publish(channel, event.model_dump_json())
    except Exception as e:
        logger.error(f"Failed to publish event '{event_type}' to '{channel}': {e}")
