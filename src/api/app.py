"""API REST asincrona del pipeline audio -> BRF.

Endpoints:
    POST /transcriptions            sube un audio y encola la transcripcion
    GET  /transcriptions/{id}       estado y metricas del trabajo
    GET  /transcriptions/{id}/brf   descarga el archivo BRF resultante
    GET  /health                    disponibilidad del servicio y del modelo

Ejecutar con:  uvicorn api.app:app --app-dir src
"""
import shutil
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from amt import AMTTranscriber
from braille_translator.brf_exporter import validate_brf
from pipeline import result_to_brf

from .jobs import MAX_SCOPE_DURATION_S, Job, JobStore

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def create_app(transcriber_factory: Optional[Callable[[], object]] = None) -> FastAPI:
    """transcriber_factory permite inyectar un transcriptor falso en pruebas."""
    @asynccontextmanager
    async def lifespan(_app):
        yield
        store.shutdown()
        shutil.rmtree(workdir, ignore_errors=True)

    app = FastAPI(title="amt-braille-translator", version="0.1.0", lifespan=lifespan)
    workdir = Path(tempfile.mkdtemp(prefix="amt_api_"))
    factory = transcriber_factory or AMTTranscriber
    transcriber_holder = {}

    def get_transcriber():
        if "t" not in transcriber_holder:
            transcriber_holder["t"] = factory()
        return transcriber_holder["t"]

    def process(job: Job, audio_path: Path, params: dict) -> None:
        brf_path = workdir / f"{job.id}.brf"
        t0 = time.time()
        result = get_transcriber().transcribe(str(audio_path))
        result_to_brf(result, output_path=str(brf_path), **params)
        job.latency_s = round(time.time() - t0, 3)

        job.audio_duration_s = round(result.duration_s, 3) or None
        if job.audio_duration_s:
            job.latency_norm = round(job.latency_s / job.audio_duration_s, 4)
            job.within_scope = job.audio_duration_s <= MAX_SCOPE_DURATION_S
        job.brf_problems = validate_brf(str(brf_path))
        job.brf_valid = not job.brf_problems
        job.brf_path = str(brf_path)

    store = JobStore(process)
    app.state.store = store

    @app.get("/health")
    def health():
        return {"status": "ok", "model_available": AMTTranscriber.available()}

    @app.post("/transcriptions", status_code=202)
    async def create_transcription(
        file: UploadFile = File(...),
        tempo_bpm: float = Form(60.0),
        beats: int = Form(4),
        beat_type: int = Form(4),
        fifths: int = Form(0),
        measures_per_line: int = Form(4),
    ):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(415, f"formato no soportado: '{suffix or '?'}' "
                                     f"(aceptados: {sorted(ALLOWED_EXTENSIONS)})")

        job = store.create(filename=file.filename or "")
        audio_path = workdir / f"{job.id}{suffix}"
        size = 0
        with open(audio_path, "wb") as out:
            while chunk := await file.read(1 << 20):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    out.close()
                    audio_path.unlink(missing_ok=True)
                    raise HTTPException(413, "archivo de mas de 100 MB")
                out.write(chunk)

        params = {"tempo_bpm": tempo_bpm, "beats": beats, "beat_type": beat_type,
                  "fifths": fifths, "measures_per_line": measures_per_line}
        store.submit(job, audio_path, params)
        return {"id": job.id, "status": job.status}

    @app.get("/transcriptions/{job_id}")
    def get_transcription(job_id: str):
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404, "trabajo no encontrado")
        return job.public()

    @app.get("/transcriptions/{job_id}/brf")
    def download_brf(job_id: str):
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404, "trabajo no encontrado")
        if job.status == "error":
            raise HTTPException(500, job.error)
        if job.status != "done":
            raise HTTPException(409, f"el trabajo esta '{job.status}'; reintentar luego")
        stem = Path(job.filename).stem or job.id
        return FileResponse(job.brf_path, media_type="application/octet-stream",
                            filename=f"{stem}.brf")

    return app


app = create_app()
