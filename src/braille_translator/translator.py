"""Traductor AST -> celdas Braille por compas 

Serializa cada compas de cada mano aplicando la FSM de octavas y alteraciones.
El resultado es una lista de cadenas Braille Unicode, una por compas, que el
renderizador Bar-over-bar alinea despues.
"""
from typing import List

from . import braille_tables as bt
from .fsm import AccidentalState, OctaveState
from .model import Chord, Hand, Note, Rest, Score


class HandTranslator:
    def __init__(self, score: Score, hand: Hand) -> None:
        self.hand = hand
        self.octave_state = OctaveState()
        self.accidental_state = AccidentalState(score.key_signature_alterations())

    def _emit_note(self, note: Note, force_octave: bool = False) -> str:
        out = []

        alter = self.accidental_state.accidental_to_emit(note)
        if alter is not None:
            out.append(bt.ACCIDENTAL[alter])

        if force_octave:
            self.octave_state.observe(note)
            out.append(bt.OCTAVE_SIGN[note.octave])
        elif self.octave_state.needs_octave_sign(note):
            out.append(bt.OCTAVE_SIGN[note.octave])

        out.append(bt.note_cell(note.step, note.duration_type))
        out.append(bt.DOT * note.dots)                      
        return "".join(out)

    def _emit_chord(self, chord: Chord) -> str:
        """Reglas 5-1/5-2/5-3: nota principal + intervalos."""
        principal = chord.principal(self.hand.side)
        principal.duration_type = chord.duration_type
        principal.dots = chord.dots
        out = [self._emit_note(principal)]

        for sec in chord.secondary(self.hand.side):
            alter = self.accidental_state.accidental_to_emit(sec)
            if alter is not None:
                out.append(bt.ACCIDENTAL[alter])
            interval = abs(sec.diatonic_index - principal.diatonic_index) + 1
            while interval > 8:
                interval -= 7
            out.append(bt.INTERVAL[interval])
        return "".join(out)

    def translate_measure(self, measure) -> str:
        self.accidental_state.start_measure()               
        parts: List[str] = []
        for ev in measure.events:
            if isinstance(ev, Rest):
                parts.append(bt.REST[ev.duration_type] + bt.DOT * ev.dots)
            elif isinstance(ev, Chord):
                parts.append(self._emit_chord(ev))
            elif isinstance(ev, Note):
                parts.append(self._emit_note(ev))
        return "".join(parts)

    def translate(self) -> List[str]:
        """Devuelve la lista de compases traducidos de esta mano."""
        self.octave_state.reset()
        result = []
        for i, measure in enumerate(self.hand.measures):
            if i == 0:
                self.octave_state.reset()                    
            result.append(self.translate_measure(measure))
        return result


def translate_score(score: Score):
    """Traduce ambas manos. Devuelve (compases_md, compases_mi)."""
    rh = HandTranslator(score, score.right).translate()
    lh = HandTranslator(score, score.left).translate()
    return rh, lh
