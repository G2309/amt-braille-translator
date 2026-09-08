"""Gestion del ciclo de vida de las transcripciones.

Cada trabajo pasa por queued -> processing -> done | error. El procesamiento
corre en un pool de hilos porque la inferencia es bloqueante.
"""
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

MAX_SCOPE_DURATION_S = 300.0   # el criterio de latencia solo aplica hasta 5 min


@dataclass
class Job:
    id: str
    status: str = "queued"                 # queued | processing | done | error
    filename: str = ""
    created_at: float = field(default_factory=time.time)
    error: str = ""
    audio_duration_s: Optional[float] = None
    latency_s: Optional[float] = None
    latency_norm: Optional[float] = None
    within_scope: Optional[bool] = None    # duracion <= 5 min
    brf_valid: Optional[bool] = None
    brf_problems: list = field(default_factory=list)
    brf_path: str = ""

    def public(self) -> dict:
        data = asdict(self)
        data.pop("brf_path")
        return data


class JobStore:
    """Registro en memoria de trabajos, con procesamiento en segundo plano."""

    def __init__(self, process: Callable[["Job", Path, dict], None], max_workers: int = 1):
        self._process = process
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers)

    def create(self, filename: str) -> Job:
        job = Job(id=uuid.uuid4().hex, filename=filename)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def submit(self, job: Job, audio_path: Path, params: dict) -> None:
        self._pool.submit(self._run, job, audio_path, params)

    def _run(self, job: Job, audio_path: Path, params: dict) -> None:
        job.status = "processing"
        try:
            self._process(job, audio_path, params)
            job.status = "done"
        except Exception as exc:
            job.status = "error"
            job.error = f"{type(exc).__name__}: {exc}"

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False)
