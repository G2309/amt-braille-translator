from dataclasses import dataclass, field
from typing import List

MIDDLE_C_MIDI = 60


@dataclass(frozen=True)
class NoteEvent:
    onset_s: float
    offset_s: float
    midi_pitch: int
    velocity: int = 80

    def __post_init__(self) -> None:
        if self.offset_s < self.onset_s:
            raise ValueError(f"offset_s ({self.offset_s}) anterior a onset_s ({self.onset_s})")
        if not 0 <= self.midi_pitch <= 127:
            raise ValueError(f"midi_pitch fuera de rango MIDI: {self.midi_pitch}")

    @property
    def duration_s(self) -> float:
        return self.offset_s - self.onset_s


@dataclass(frozen=True)
class PedalEvent:
    onset_s: float
    offset_s: float


@dataclass
class TranscriptionResult:
    notes: List[NoteEvent] = field(default_factory=list)
    pedals: List[PedalEvent] = field(default_factory=list)
    duration_s: float = 0.0
    source: str = ""
    model_name: str = ""

    def sorted_notes(self) -> List[NoteEvent]:
        return sorted(self.notes, key=lambda n: (n.onset_s, n.midi_pitch))

    def split_hands(self, split_pitch: int = MIDDLE_C_MIDI):
        """Do central hacia arriba es mano derecha. No modela cruces de manos."""
        right = [n for n in self.notes if n.midi_pitch >= split_pitch]
        left = [n for n in self.notes if n.midi_pitch < split_pitch]
        return right, left
