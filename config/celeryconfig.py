# Celery production config
broker_url = "redis://redis:6379/0"
result_backend = "redis://redis:6379/0"
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True
task_track_started = True
task_time_limit = 300  # 5 minutes
worker_max_tasks_per_child = 100
