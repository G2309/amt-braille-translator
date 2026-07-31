"""Modulo AMT: audio -> eventos -> AST musical."""
from .events import MIDDLE_C_MIDI, NoteEvent, PedalEvent, TranscriptionResult
from .quantizer import midi_to_note, quantize, ticks_per_measure
from .transcriber import AMTTranscriber

__all__ = [
    "NoteEvent", "PedalEvent", "TranscriptionResult", "MIDDLE_C_MIDI",
    "quantize", "midi_to_note", "ticks_per_measure", "AMTTranscriber",
]
