"""
Performance Optimization - Caching, profiling, and latency optimization.
"""

import time
import functools
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Tuple


class LRUCache:
    """Thread-safe LRU cache for common operations."""

    def __init__(self, max_size: int = 256):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Tuple[bool, Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self.hits += 1
                return True, self._cache[key]
            self.misses += 1
            return False, None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def __len__(self) -> int:
        return len(self._cache)


def cached(cache: LRUCache, key_fn: Optional[Callable] = None):
    """Decorator to cache function results in an LRUCache."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = key_fn(*args, **kwargs) if key_fn else str(args) + str(kwargs)
            found, value = cache.get(key)
            if found:
                return value
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        return wrapper
    return decorator


class PerformanceProfiler:
    """Lightweight profiler for tracking operation latencies."""

    def __init__(self):
        self._timings: Dict[str, list] = {}

    def record(self, operation: str, elapsed_ms: float) -> None:
        self._timings.setdefault(operation, []).append(elapsed_ms)

    def time(self, operation: str):
        """Context manager for timing a block."""
        return _TimingContext(self, operation)

    def get_stats(self, operation: str) -> Dict[str, float]:
        times = self._timings.get(operation, [])
        if not times:
            return {}
        return {
            "count": len(times),
            "avg_ms": sum(times) / len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else max(times),
        }

    def report(self) -> Dict[str, Dict]:
        return {op: self.get_stats(op) for op in self._timings}


class _TimingContext:
    def __init__(self, profiler: PerformanceProfiler, operation: str):
        self._profiler = profiler
        self._operation = operation
        self._start: float = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_):
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        self._profiler.record(self._operation, elapsed_ms)


# Global shared instances
response_cache = LRUCache(max_size=512)
profiler = PerformanceProfiler()
