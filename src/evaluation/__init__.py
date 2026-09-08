"""Medicion de la calidad del Braille generado y de la latencia del pipeline."""
from .bsa import (
    CATEGORY_WEIGHTS, BsaResult, CategoryScore,
    classify_cells, compare_files, compute_bsa, load_braille,
)
from .latency import (
    LATENCY_THRESHOLD, MIN_RUNS_WITHIN, LatencyRun, LatencySummary, StageTimings,
    measure_end_to_end, synthetic_result, time_deterministic,
)

__all__ = [
    "CATEGORY_WEIGHTS", "BsaResult", "CategoryScore",
    "classify_cells", "compare_files", "compute_bsa", "load_braille",
    "LATENCY_THRESHOLD", "MIN_RUNS_WITHIN", "LatencyRun", "LatencySummary",
    "StageTimings", "measure_end_to_end", "synthetic_result", "time_deterministic",
]
