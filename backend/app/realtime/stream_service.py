# stream_service.py - Service for managing data streams.
import os
import json
import time
import logging
import redis.asyncio as aioredis
from typing import AsyncGenerator
from app.realtime.event_models import StreamEvent

logger = logging.getLogger(__name__)

class StreamService:
    def __init__(self):
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        self.redis = aioredis.Redis(host=host, port=port, decode_responses=True)
    
    def _get_channel(self, job_id: str) -> str:
        return f"stream:{job_id}"

    async def publish_event(self, job_id: str, event_type: str, data: dict):
        """Publish an event to the Redis channel for a specific job."""
        event = StreamEvent(
            event_type=event_type,
            job_id=job_id,
            data=data,
            timestamp=time.time()
        )
        channel = self._get_channel(job_id)
        try:
            await self.redis.publish(channel, event.model_dump_json())
            logger.debug(f"Published event '{event_type}' to '{channel}'")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    async def subscribe(self, job_id: str) -> AsyncGenerator[str, None]:
        """Subscribe to a job's Redis channel and yield messages as they arrive."""
        channel = self._get_channel(job_id)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel '{channel}'")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message["data"]
        except Exception as e:
            logger.error(f"Error reading from pubsub: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

_stream_service = None

def get_stream_service() -> StreamService:
    global _stream_service
    if _stream_service is None:
        _stream_service = StreamService()
    return _stream_service
