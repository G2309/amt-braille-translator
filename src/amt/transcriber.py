"""Wrapper de piano_transcription_inference 
"""
from typing import Optional

from .events import NoteEvent, PedalEvent, TranscriptionResult

MODEL_NAME = "Kong et al. 2021 (piano_transcription_inference)"


class AMTTranscriber:
    def __init__(self, checkpoint_path: Optional[str] = None, device: str = "cpu") -> None:
        self.checkpoint_path = checkpoint_path
        self.device = device
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
            self._model = PianoTranscription(device=self.device, checkpoint_path=self.checkpoint_path)
            self._sample_rate = sample_rate
        return self._model

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        import librosa

        model = self._load()
        audio, _ = librosa.load(audio_path, sr=self._sample_rate, mono=True)
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
