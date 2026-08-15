from __future__ import annotations

from functools import wraps
from time import monotonic, perf_counter
from typing import Any, Callable, TypeVar, ParamSpec

from src.analytics import record_data_quality, record_error, record_performance

P = ParamSpec("P")
R = TypeVar("R")

# Avoid writing a data-quality row on every Streamlit rerun/request.
_DQ_LAST: dict[tuple[str, str, str], float] = {}
_DQ_INTERVAL_SECONDS = 300.0


def _maybe_record_quality(source: str | None, check: str | None, status: str, metadata: dict[str, Any] | None = None) -> None:
    if not source or not check:
        return
    key = (source, check, status)
    now = monotonic()
    last = _DQ_LAST.get(key, 0.0)
    if now - last < _DQ_INTERVAL_SECONDS:
        return
    _DQ_LAST[key] = now
    record_data_quality(source, check, status, metadata=metadata)


def observe_operation(
    component: str,
    operation: str | None = None,
    *,
    quality_source: str | None = None,
    quality_check: str | None = "availability",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for private performance/error observability.

    It never changes the public return value and re-raises the original error.
    Technical details are stored only by the private analytics layer.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        op = operation or func.__name__
        perf_name = f"{component}.{op}"

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            started = perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                elapsed = (perf_counter() - started) * 1000.0
                record_performance(perf_name, elapsed, success=False, metadata={"component": component})
                record_error(exc, component=component, operation=op, metadata={"duration_ms": round(elapsed, 2)})
                _maybe_record_quality(quality_source, quality_check, "degraded", {"operation": op})
                raise
            elapsed = (perf_counter() - started) * 1000.0
            record_performance(perf_name, elapsed, success=True, metadata={"component": component})
            _maybe_record_quality(quality_source, quality_check, "ok", {"operation": op})
            return result

        return wrapper

    return decorator
