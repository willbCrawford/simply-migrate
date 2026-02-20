class Config:
    """Configuration for Celery and Redis"""
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 1  # Separate DB for migration state

    # Task configuration
    TASK_SOFT_TIME_LIMIT = 3600  # 1 hour
    TASK_TIME_LIMIT = 3900  # 1 hour 5 minutes (hard limit)
    TASK_ACKS_LATE = True
    TASK_REJECT_ON_WORKER_LOST = True
