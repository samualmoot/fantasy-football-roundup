import threading
from typing import Callable, Any, Dict
from django.core.cache import cache


JOB_TTL_SECONDS = 60 * 60  # 1 hour
IN_PROGRESS = "__IN_PROGRESS__"


def _run_and_store(cache_key: str, func: Callable[[], Dict[str, Any]]) -> None:
    try:
        result = func()
    except Exception as exc:
        result = {"error": str(exc)}
    cache.set(cache_key, result, JOB_TTL_SECONDS)


def schedule_job(cache_key: str, func: Callable[[], Dict[str, Any]]) -> None:
    """Start a daemon thread to compute result and store in cache."""
    t = threading.Thread(target=_run_and_store, args=(cache_key, func), daemon=True)
    t.start()


def ensure_job(cache_key: str, func: Callable[[], Dict[str, Any]]) -> str:
    """Ensure a job is running or cached.

    Returns one of: 'ready', 'pending'.
    """
    val = cache.get(cache_key)
    if val is None:
        # mark as in progress and schedule
        cache.set(cache_key, IN_PROGRESS, JOB_TTL_SECONDS)
        schedule_job(cache_key, func)
        return "pending"
    if val == IN_PROGRESS:
        return "pending"
    return "ready"


def get_job_result(cache_key: str) -> Dict[str, Any] | None:
    val = cache.get(cache_key)
    if val in (None, IN_PROGRESS):
        return None
    return val  # type: ignore[return-value]


