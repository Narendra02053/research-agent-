"""
celery_app.py
Initializes the Celery application with Redis as the message broker.
Configures task serialization, retries, and worker settings.
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/2"
RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/3"

celery_app = Celery(
    "deep_research_worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.workers.research_tasks"]
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timeouts & retries
    task_soft_time_limit=300,       # 5 minutes soft limit
    task_time_limit=360,            # 6 minutes hard limit
    task_acks_late=True,            # Acknowledge after completion (reliability)
    worker_prefetch_multiplier=1,   # One task at a time per worker (heavy tasks)

    # Result expiry
    result_expires=86400,           # Results expire after 24 hours

    # Retry policy for broker connection
    broker_connection_retry_on_startup=True,

    # Task routing (future: separate queues per agent type)
    task_default_queue="research",
)
