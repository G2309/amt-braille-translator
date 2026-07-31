"""Maquina de Estados Finitos del traductor 

Gestiona los dos estados de la transcripcion:

1. OctaveState  — Reglas 2-2 / 2-3 / 2-4 del subset (signos de octava).
2. AccidentalState — Reglas 3-2 / 3-3 / 3-4 (vigencia de alteraciones).
"""
from typing import Optional

from .model import Note


class OctaveState:
    """Regla 2-3: decidir si una nota lleva signo de octava.

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
        """Regla 2-2 / 15-2: inicio de pieza, de linea o tras signo de mano."""
        self._prev = None

    def needs_octave_sign(self, note: Note) -> bool:
        prev = self._prev
        self._prev = note
        if prev is None:
            return True                                   # Regla 2-2
        interval = abs(note.diatonic_index - prev.diatonic_index) + 1
        if interval <= 3:
            return False
        if interval in (4, 5):
            return note.octave != prev.octave
        return True                                       # 6a o mayor

    def observe(self, note: Note) -> None:
        """Actualiza la referencia sin emitir (p.ej. tras intervalos, Regla 2-4)."""
        self._prev = note


class AccidentalState:
    """Reglas 3-2 / 3-3 / 3-4: vigencia de alteraciones dentro del compas.

    Estado: dict (step, octave) -> alter vigente.
    Al inicio de cada compas se reinicia con la armadura de la clave;
    la armadura afecta a la letra en TODAS las octavas.
    """

    def __init__(self, key_alterations: dict) -> None:
        self._key = dict(key_alterations)     # step -> alter (armadura)
        self._active: dict = {}

    def start_measure(self) -> None:
        """Regla 3-2: reset al estado de la armadura en cada compas."""
        self._active = {}

    def _expected(self, step: str, octave: int) -> int:
        if (step, octave) in self._active:
            return self._active[(step, octave)]
        return self._key.get(step, 0)

    def accidental_to_emit(self, note: Note) -> Optional[int]:
        """Devuelve el alter a emitir (o None si la alteracion ya esta vigente).

        Emite becuadro (0) cuando hay que cancelar una alteracion vigente
        (Regla 3-3).
        """
        expected = self._expected(note.step, note.octave)
        if note.alter == expected:
            return None
        self._active[(note.step, note.octave)] = note.alter
        return note.alter
