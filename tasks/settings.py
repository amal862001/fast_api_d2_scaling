from arq.connections import RedisSettings
from config import settings
from tasks.worker import generate_agency_report   


# WorkerSettings is the configuration class that Arq looks for when running a worker with `python -m arq tasks.settings.WorkerSettings`
class WorkerSettings:
    functions      = [generate_agency_report]
    redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
    max_jobs       = 10
    job_timeout    = 120
    keep_result    = 3600