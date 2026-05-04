import redis
import json
from app.core.config import settings

r = redis.from_url(settings.REDIS_URL)

CACHE_TTL = 3600  # 1시간


def get_cached_job(url: str) -> dict | None:
    data = r.get(f"job:{url}")
    if data:
        return json.loads(data)
    return None


def set_cached_job(url: str, job_info: dict):
    r.set(f"job:{url}", json.dumps(job_info, ensure_ascii=False), ex=CACHE_TTL)