import gc
import time
import tracemalloc

import pytest

from tsp.instrument import Profiler

MB = 1_000_000


def by_name(prof: Profiler) -> dict[str, dict]:
    return {r["subroutine"]: r for r in prof.records()}


def test_counts_calls_and_time():
    prof = Profiler()
    for _ in range(3):
        with prof.timed("sleep"):
            time.sleep(0.01)
    rec = by_name(prof)["sleep"]
    assert rec["calls"] == 3
    assert rec["time_s"] >= 0.03
    assert rec["peak_bytes"] is None


def test_records_time_on_exception():
    prof = Profiler()
    with pytest.raises(RuntimeError):
        with prof.timed("fails"):
            time.sleep(0.01)
            raise RuntimeError
    assert by_name(prof)["fails"]["time_s"] >= 0.01


def test_time_mode_does_not_trace_memory():
    prof = Profiler()
    with prof.timed("x"):
        pass
    assert not tracemalloc.is_tracing()


def test_memory_peak():
    with Profiler(memory=True) as prof:
        with prof.timed("alloc"):
            buf = bytearray(10 * MB)
            del buf
    assert by_name(prof)["alloc"]["peak_bytes"] >= 10 * MB
    assert not tracemalloc.is_tracing()  # desligado ao sair do with


def test_nested_peak_propagates_to_outer():
    with Profiler(memory=True) as prof:
        with prof.timed("outer"):
            # Pico do trecho de fora ANTES do de dentro: não pode se perder no reset
            big = bytearray(8 * MB)
            del big
            with prof.timed("inner"):
                small = bytearray(5 * MB)
                del small
    recs = by_name(prof)
    assert 5 * MB <= recs["inner"]["peak_bytes"] < 8 * MB
    assert recs["outer"]["peak_bytes"] >= 8 * MB


def test_counts_gc_collections():
    prof = Profiler()
    gc.collect()
    assert prof.gc_collections() >= 1
