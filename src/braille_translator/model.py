"""AST musical del sistema 

El AST es la representacion intermedia entre el parser (MusicXML o, en Fase 4,
la salida del modulo AMT) y el traductor Braille. 
"""
from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class Note:
    step: str                 # C D E F G A B
    octave: int               # 1..7 (octavas Braille; 4 = octava central)
    duration_type: str        # whole half quarter eighth 16th 32nd 64th 128th
    alter: int = 0            # -2..+2 (0 = natural)
    dots: int = 0             # puntillos
    explicit_accidental: bool = False  # el MusicXML trae explicito
    tie: bool = False         # ligada a la siguiente nota del mismo sonido

    @property
    def diatonic_index(self) -> int:
        """Indice diatonico absoluto para calculo de intervalos."""
        steps = "CDEFGAB"
        return self.octave * 7 + steps.index(self.step)


@dataclass
class Chord:
    notes: List[Note]         # todas las notas del acorde
    duration_type: str
    dots: int = 0
    tie: bool = False

    def principal(self, hand: str) -> Note:
        ordered = sorted(self.notes, key=lambda n: n.diatonic_index)
        return ordered[-1] if hand == "right" else ordered[0]

    def secondary(self, hand: str) -> List[Note]:
        ordered = sorted(self.notes, key=lambda n: n.diatonic_index)
        if hand == "right":
            return list(reversed(ordered[:-1]))   # descendente desde la aguda
        return ordered[1:]                        # ascendente desde la grave


@dataclass
class Rest:
    duration_type: str
    dots: int = 0


Event = Union[Note, Chord, Rest]


@dataclass
class Measure:
    number: int
    events: List[Event] = field(default_factory=list)
    # Voces simultaneas adicionales de la misma mano. Cada una se escribe
    # completa y separada de la anterior por el signo de cópula.
    extra_voices: List[List[Event]] = field(default_factory=list)

    def voices(self) -> List[List[Event]]:
        return [self.events] + self.extra_voices


@dataclass
class Hand:
    side: str                            # "right" | "left"
    measures: List[Measure] = field(default_factory=list)


@dataclass
class Score:
    title: str = ""
    beats: int = 4
    beat_type: int = 4
    fifths: int = 0                      # armadura: + sostenidos, - bemoles
    right: Hand = field(default_factory=lambda: Hand("right"))
    left: Hand = field(default_factory=lambda: Hand("left"))

    def key_signature_alterations(self) -> dict:
        """Regla 3-4: mapa (step -> alter) derivado de la armadura."""
        sharps = ["F", "C", "G", "D", "A", "E", "B"]
        flats = ["B", "E", "A", "D", "G", "C", "F"]
        result = {}
        if self.fifths > 0:
            for s in sharps[: self.fifths]:
                result[s] = 1
        elif self.fifths < 0:
            for f in flats[: -self.fifths]:
                result[f] = -1
        return result
