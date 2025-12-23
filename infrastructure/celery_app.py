"""
Celery application configuration
"""
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "product_hunt_scraper",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["infrastructure.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=30 * 60,
)

# Celery Beat schedule - Multiple cron jobs (10 minute cycles)

celery_app.conf.beat_schedule = {

    # STEP 1: Scrape every 10 minutes
    "auto-scrape-every-10-minutes": {
        "task": "tasks.auto_scrape_yesterday",
        "schedule": crontab(minute="*/10"),   # Every 10 minutes
    },

    # STEP 2: Enrich 10 minutes after scrape
    "auto-enrich-10-min-after": {
        "task": "tasks.auto_enrich_task",
        "schedule": crontab(minute="5,15,25,35,45,55"),  # 10 min after scrape
    },

    # STEP 3: Analyze 10 minutes after enrich (20 min after scrape)
    "auto-analyze-20-min-after-scrape": {
        "task": "tasks.auto_analyze_task",
        "schedule": crontab(minute="0,10,20,30,40,50"),  # 20 min after scrape
    },
}


if __name__ == "__main__":
    celery_app.start()
