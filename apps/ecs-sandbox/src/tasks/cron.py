"""
Declarative cron tasks with distributed Redis locking.

Single-instance deployment — the lock prevents overlapping runs if a previous
invocation is still in progress. If you scale to multiple instances, the same
lock ensures only one instance runs each cron tick.

Usage:
    from src.tasks.cron import cron

    @cron("*/5 * * * *")
    async def my_periodic_task() -> dict:
        return {"result": "done"}
"""

import inspect
from dataclasses import dataclass
from typing import Any, Callable

from redis.asyncio import Redis
from taskiq import TaskiqDepends

from src.tasks.deps import get_redis

_cron_registry: dict[str, "CronConfig"] = {}


@dataclass
class CronConfig:
    expression: str
    lock_ttl: int
    task_name: str


class TaskLock:
    KEY_PREFIX = "taskiq:lock:"

    def __init__(self, redis: Redis):
        self._redis = redis

    async def acquire(self, name: str, ttl_seconds: int) -> bool:
        key = f"{self.KEY_PREFIX}{name}"
        result = await self._redis.set(key, "1", nx=True, ex=ttl_seconds)
        return result is not None

    async def release(self, name: str) -> None:
        key = f"{self.KEY_PREFIX}{name}"
        await self._redis.delete(key)


def cron(expression: str, lock_ttl: int = 300) -> Callable[..., Any]:
    """Register a function as a scheduled cron task with distributed locking."""

    def decorator(func: Any) -> Any:
        task_name = func.__name__

        _cron_registry[task_name] = CronConfig(
            expression=expression,
            lock_ttl=lock_ttl,
            task_name=task_name,
        )

        async def wrapper(
            *args: Any,
            _cron_redis: Redis = TaskiqDepends(get_redis),
            **kwargs: Any,
        ) -> dict[str, Any]:
            lock = TaskLock(_cron_redis)

            if not await lock.acquire(task_name, lock_ttl):
                return {"skipped": True, "reason": "lock_held"}

            try:
                result = await func(*args, **kwargs)
                return result if isinstance(result, dict) else {"result": result}
            finally:
                await lock.release(task_name)

        # Merge the original function's signature with the injected cron params
        orig_sig = inspect.signature(func)
        wrapper_sig = inspect.signature(wrapper)
        cron_params = {
            k: v for k, v in wrapper_sig.parameters.items() if k.startswith("_cron_")
        }
        combined_params = list(orig_sig.parameters.values()) + list(
            cron_params.values()
        )
        wrapper.__signature__ = orig_sig.replace(parameters=combined_params)  # type: ignore[attr-defined]
        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        wrapper.__module__ = func.__module__

        from src.tasks import broker

        return broker.task(schedule=[{"cron": expression}])(wrapper)

    return decorator


def get_cron_registry() -> dict[str, CronConfig]:
    return _cron_registry.copy()
