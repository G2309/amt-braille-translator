"""Maquina de estados del traductor.

Lleva los dos contextos que el Braille necesita arrastrar: en que octava
quedo la ultima nota y que alteraciones siguen vigentes en el compas.
"""
from typing import Optional

from .model import Note


class OctaveState:
    """Decide si una nota necesita signo de octava.

    | Intervalo con la nota previa | Cambia de octava | Se emite signo |
    |------------------------------|------------------|----------------|
    | unisono, 2a, 3a              | (cualquiera)     | NO             |
    | 4a, 5a                       | si               | SI             |
    | 4a, 5a                       | no               | NO             |
    | 6a o mayor                   | (cualquiera)     | SI             |
    """

    def __init__(self) -> None:
        self._prev: Optional[Note] = None

    def reset(self) -> None:
        self._prev = None

    def needs_octave_sign(self, note: Note) -> bool:
        prev = self._prev
        self._prev = note
        if prev is None:
            return True                                   # primera nota del renglon
        interval = abs(note.diatonic_index - prev.diatonic_index) + 1
        if interval <= 3:
            return False
        if interval in (4, 5):
            return note.octave != prev.octave
        return True                                       # 6a o mayor

    def observe(self, note: Note) -> None:
        self._prev = note


class AccidentalState:
    """Alteraciones vigentes dentro del compas.

    Estado: dict (step, octave) -> alter vigente.
    Al inicio de cada compas se reinicia con la armadura de la clave;
    la armadura afecta a la letra en TODAS las octavas.
    """

    def __init__(self, key_alterations: dict) -> None:
        self._key = dict(key_alterations)     
        self._active: dict = {}

    def start_measure(self) -> None:
        self._active = {}

    def _expected(self, step: str, octave: int) -> int:
        if (step, octave) in self._active:
            return self._active[(step, octave)]
        return self._key.get(step, 0)

    def accidental_to_emit(self, note: Note) -> Optional[int]:
        """Devuelve el alter a emitir (o None si la alteracion ya esta vigente).

        Devuelve becuadro (0) cuando hay que cancelar una alteracion vigente.
        """
        expected = self._expected(note.step, note.octave)
        if note.alter == expected:
            return None
        self._active[(note.step, note.octave)] = note.alter
        return note.alter
