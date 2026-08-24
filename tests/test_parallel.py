"""Parallel tests: Dask chunk map must equal the sequential result."""

from nanotrack.parallel import chunk_map


def _square_chunk(chunk):
    return [x * x for x in chunk]


def test_chunk_map_matches_sequential():
    items = list(range(100))
    assert chunk_map(_square_chunk, items, chunk_size=7) == [x * x for x in items]


def test_chunk_map_matches_sequential_single_threaded():
    items = list(range(50))
    got = chunk_map(_square_chunk, items, chunk_size=8, scheduler="single-threaded")
    assert got == [x * x for x in items]


def test_chunk_map_empty():
    assert chunk_map(_square_chunk, [], chunk_size=8) == []
