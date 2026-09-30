"""Wrapper de piano_transcription_inference 
"""
import hashlib
import urllib.request
from pathlib import Path
from typing import Optional

from .events import NoteEvent, PedalEvent, TranscriptionResult

MODEL_NAME = "Kong et al. 2021 (piano_transcription_inference)"

# Checkpoint del ajuste fino (notebooks/amt-finetune.ipynb, version 3 en Kaggle),
# publicado como archivo del release para que se descargue sin credenciales
FINETUNED_URL = (
    "https://github.com/G2309/amt-braille-translator/releases/download/"
    "modelo-ajustado-v1/kong_ajustado.pth"
)
FINETUNED_SHA256 = "7fcbdc9969259c5572975d31646dfef53aa67b923411a6c94ca0186652f63d5f"
CACHE_DIR = Path.home() / "piano_transcription_inference_data"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def resolve_checkpoint(checkpoint: Optional[str]) -> Optional[str]:
    """Ruta del checkpoint a cargar.

    original o None usa el checkpoint publicado de Kong, que el paquete baja
    solo. ajustado baja el del ajuste fino la primera vez y verifica su hash.
    Cualquier otro valor se toma como ruta a un archivo.
    """
    if checkpoint in (None, "original"):
        return None
    if checkpoint != "ajustado":
        return checkpoint
    destino = CACHE_DIR / "kong_ajustado.pth"
    if not destino.exists() or _sha256(destino) != FINETUNED_SHA256:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_suffix(".part")
        urllib.request.urlretrieve(FINETUNED_URL, parcial)
        if _sha256(parcial) != FINETUNED_SHA256:
            parcial.unlink(missing_ok=True)
            raise RuntimeError(
                "el checkpoint ajustado descargado no coincide con el hash esperado; "
                "usar checkpoint='original' o revisar el release"
            )
        parcial.replace(destino)
    return str(destino)


class AMTTranscriber:
    def __init__(self, checkpoint_path: Optional[str] = "ajustado", device: str = "cpu",
                 normalize: bool = True) -> None:
        self.checkpoint_path = checkpoint_path
        self.device = device
        self.normalize = normalize
        self._model = None
        self._sample_rate = None

    @staticmethod
    def available() -> bool:
        from importlib.util import find_spec
        return find_spec("piano_transcription_inference") is not None and find_spec("librosa") is not None

    def _load(self):
        if self._model is None:
            try:
                from piano_transcription_inference import PianoTranscription, sample_rate
            except ImportError as exc:
                raise ImportError(
                    "Falta piano_transcription_inference. Instalar con "
                    "'pip install -r requirements.txt'."
                ) from exc
            self._model = PianoTranscription(device=self.device,
                                             checkpoint_path=resolve_checkpoint(self.checkpoint_path))
            self._sample_rate = sample_rate
        return self._model

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        import librosa

        model = self._load()
        audio, _ = librosa.load(audio_path, sr=self._sample_rate, mono=True)
        if self.normalize:
            from .audio import normalize_loudness
            audio = normalize_loudness(audio)
        output = model.transcribe(audio, None)
        return self.from_model_output(output, source=audio_path, duration_s=len(audio) / self._sample_rate)

    @staticmethod
    def from_model_output(output: dict, source: str = "", duration_s: float = 0.0) -> TranscriptionResult:
        """Convierte la salida cruda del modelo al contrato de eventos."""
        notes = [
            NoteEvent(
                onset_s=float(n["onset_time"]),
                offset_s=float(n["offset_time"]),
                midi_pitch=int(n["midi_note"]),
                velocity=int(n.get("velocity", 80)),
            )
            for n in output.get("est_note_events", [])
        ]
        pedals = [
            PedalEvent(onset_s=float(p["onset_time"]), offset_s=float(p["offset_time"]))
            for p in output.get("est_pedal_events", [])
        ]
        return TranscriptionResult(
            notes=notes,
            pedals=pedals,
            duration_s=duration_s,
            source=source,
            model_name=MODEL_NAME,
        )
