"""Traductor AST -> celdas Braille por compas

Serializa cada compas de cada mano aplicando la FSM de octavas y alteraciones.
El resultado es una lista de cadenas Braille Unicode, una por compas, que el
renderizador Bar-over-bar alinea despues.
"""
import copy
from typing import List

from . import braille_tables as bt
from .fsm import AccidentalState, OctaveState
from .model import Chord, Hand, Measure, MultiRest, Note, Rest, Score
from .renderer import DEFAULT_MEASURES_PER_LINE


class HandTranslator:
    def __init__(self, score: Score, hand: Hand) -> None:
        self.hand = hand
        self.octave_state = OctaveState()
        self.accidental_state = AccidentalState(score.key_signature_alterations())
        self._new_line = False

    def _accidental_cells(self, note: Note) -> str:
        alter = self.accidental_state.accidental_to_emit(note)
        if alter is None:
            return ""
        # una nota que viene ligada solo repite la alteracion si abre renglon
        if note.tie_from_prev and not self._new_line:
            return ""
        return bt.ACCIDENTAL[alter]

    def _emit_note(self, note: Note, force_octave: bool = False,
                   suppress_tie: bool = False) -> str:
        out = []
        if note.slur_open:
            out.append(bt.SLUR_OPEN)

        out.append(self._accidental_cells(note))

        if force_octave:
            self.octave_state.observe(note)
            out.append(bt.OCTAVE_SIGN[note.octave])
        elif self.octave_state.needs_octave_sign(note):
            out.append(bt.OCTAVE_SIGN[note.octave])

        out.append(bt.note_cell(note.step, note.duration_type))
        out.append(bt.DOT * note.dots)
        # la ligadura de expresion va antes que la de prolongacion
        if note.slur:
            out.append(bt.SLUR)
        if note.slur_close:
            out.append(bt.SLUR_CLOSE)
        if note.tie and not suppress_tie:
            out.append(bt.TIE)
        return "".join(out)

    def _emit_chord(self, chord: Chord) -> str:
        # se escribe la nota mas aguda en la derecha y la mas grave en la
        # izquierda; el resto del acorde va como intervalos
        principal = chord.principal(self.hand.side)
        principal.duration_type = chord.duration_type
        principal.dots = chord.dots

        out = []
        if chord.slur_open:
            out.append(bt.SLUR_OPEN)
        # si solo una nota se prolonga, la ligadura va tras ella o su
        # intervalo; si se prolonga el acorde entero, basta el signo de acorde
        out.append(self._emit_note(principal, suppress_tie=chord.tie))
        # la ligadura de expresion va tras la nota escrita, antes de los intervalos
        if chord.slur:
            out.append(bt.SLUR)

        for sec in chord.secondary(self.hand.side):
            out.append(self._accidental_cells(sec))
            interval = abs(sec.diatonic_index - principal.diatonic_index) + 1
            if interval == 1:
                # unisono, el caso de dos notas con la misma letra y octava pero
                # distinta alteracion; se escribe como octava con su signo
                out.append(bt.OCTAVE_SIGN[sec.octave])
                interval = 8
            elif interval > 8:
                # un intervalo mayor que la octava se reduce y lleva delante
                # el signo de octava de su propia nota
                out.append(bt.OCTAVE_SIGN[sec.octave])
                while interval > 8:
                    interval -= 7
            out.append(bt.INTERVAL[interval])
            if sec.tie and not chord.tie:
                out.append(bt.TIE)

        if chord.tie:
            out.append(bt.CHORD_TIE)
        if chord.slur_close:
            out.append(bt.SLUR_CLOSE)
        return "".join(out)

    @staticmethod
    def _multi_rest(count: int) -> str:
        """Hasta tres compases se repite el silencio de redonda; desde cuatro
        se escribe el numero de compases antes de un solo silencio."""
        if count <= 3:
            return bt.REST["whole"] * count
        digits = "".join(bt.UPPER_DIGIT[int(d)] for d in str(count))
        return bt.NUMBER_SIGN + digits + bt.REST["whole"]

    def _emit_voice(self, events, force_first_octave: bool) -> str:
        parts: List[str] = []
        first = force_first_octave
        for ev in events:
            if isinstance(ev, MultiRest):
                parts.append(self._multi_rest(ev.count))
            elif isinstance(ev, Rest):
                parts.append(bt.REST[ev.duration_type] + bt.DOT * ev.dots)
            elif isinstance(ev, Chord):
                parts.append(self._emit_chord(ev))
                first = False
            elif isinstance(ev, Note):
                parts.append(self._emit_note(ev, force_octave=first))
                first = False
        return "".join(parts)

    def translate_measure(self, measure, new_line: bool = False) -> str:
        self._new_line = new_line
        # cada voz arranca con signo de octava y desde la referencia con la
        # que se entro al compas, no desde donde quedo la voz anterior
        entry_state = copy.deepcopy(self.octave_state)
        rendered = []
        for i, voice in enumerate(measure.voices()):
            # las alteraciones no cruzan la copula: cada voz vuelve a la armadura
            self.accidental_state.start_measure()
            if i > 0:
                self.octave_state = copy.deepcopy(entry_state)
            rendered.append(self._emit_voice(voice, force_first_octave=i > 0))
        return bt.IN_ACCORD.join(rendered)

    def translate(self, measures_per_line: int = DEFAULT_MEASURES_PER_LINE) -> List[str]:
        """Devuelve la lista de compases traducidos de esta mano.
        measures_per_line debe coincidir con el del renderizador: marca donde
        empieza cada renglon Bar-over-bar.
        """
        result = []
        for i, measure in enumerate(self.hand.measures):
            new_line = i % measures_per_line == 0
            if new_line:
                # tras el signo de mano, la primera nota lleva octava
                self.octave_state.reset()
            result.append(self.translate_measure(measure, new_line=new_line))
        return result


def _rest_only(measure: Measure) -> bool:
    return not measure.extra_voices and all(isinstance(ev, (Rest, MultiRest)) for ev in measure.events)


def merge_rest_measures(score: Score) -> Score:
    """Compases de silencio segun el Manual.

    Un compas que en una mano es solo silencio se escribe con el silencio de
    redonda, sin importar la indicacion de compas. Si las dos manos callan
    varios compases seguidos, se agrupan en una sola paralela para que las
    barras de ambas manos sigan alineadas.
    """
    rh, lh = score.right.measures, score.left.measures
    new_rh, new_lh = [], []
    i = 0
    while i < min(len(rh), len(lh)):
        if _rest_only(rh[i]) and _rest_only(lh[i]):
            j = i
            while j < min(len(rh), len(lh)) and _rest_only(rh[j]) and _rest_only(lh[j]):
                j += 1
            new_rh.append(Measure(rh[i].number, events=[MultiRest(j - i)]))
            new_lh.append(Measure(lh[i].number, events=[MultiRest(j - i)]))
            i = j
            continue
        new_rh.append(Measure(rh[i].number, events=[MultiRest(1)]) if _rest_only(rh[i]) else rh[i])
        new_lh.append(Measure(lh[i].number, events=[MultiRest(1)]) if _rest_only(lh[i]) else lh[i])
        i += 1
    merged = Score(title=score.title, beats=score.beats, beat_type=score.beat_type, fifths=score.fifths)
    merged.right.measures, merged.left.measures = new_rh, new_lh
    return merged


def translate_score(score: Score, measures_per_line: int = DEFAULT_MEASURES_PER_LINE,
                    merge_rests: bool = True):
    """Traduce ambas manos. Devuelve (compases_md, compases_mi)."""
    if merge_rests:
        score = merge_rest_measures(score)
    rh = HandTranslator(score, score.right).translate(measures_per_line)
    lh = HandTranslator(score, score.left).translate(measures_per_line)
    return rh, lh
