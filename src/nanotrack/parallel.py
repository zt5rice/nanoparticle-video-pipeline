"""Chunked parallel map with Dask (sequential fallback)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def chunk_map(
    func: Callable[[list[T]], list[R]],
    items: list[T],
    chunk_size: int = 16,
    scheduler: str = "threads",
) -> list[R]:
    """Apply ``func`` to chunks of ``items`` (Dask delayed; sequential fallback)."""
    if chunk_size <= 0:
        chunk_size = 16
    chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
    if not chunks:
        return []
    try:
        from dask import compute, delayed
    except ImportError:
        return [r for c in chunks for r in func(c)]
    tasks = [delayed(func)(c) for c in chunks]
    results = compute(*tasks, scheduler=scheduler)
    return [r for res in results for r in res]

