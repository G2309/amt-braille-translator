# Traduce el AST a celdas Braille por compas aplicando la FSM de octavas y alteraciones
import copy
from typing import Dict, List

from . import braille_tables as bt
from .fsm import AccidentalState, OctaveState
from .model import Chord, Hand, Measure, MultiRest, Note, Rest, Score
from .renderer import DEFAULT_MEASURES_PER_LINE


# Duracion en cuartos de garrapatea; cada celda vale lo mismo para el par grande y el pequeno
_UNITS = {"whole": 512, "half": 256, "quarter": 128, "eighth": 64,
          "16th": 32, "32nd": 16, "64th": 8, "128th": 4}
_PAIR = {"whole": "16th", "half": "32nd", "quarter": "64th", "eighth": "128th"}
_PAIR.update({small: large for large, small in list(_PAIR.items())})
_LARGE = {"whole", "half", "quarter", "eighth"}


def _duration(dtype: str, dots: int) -> int:
    return sum(_UNITS[dtype] >> k for k in range(dots + 1))


def _ambiguous(events) -> bool:
    # Hay ambiguedad si otra lectura grande o pequena de las mismas celdas completa igual el compas
    target = sum(_duration(ev.duration_type, ev.dots) for ev in events)
    states = {(0, False)}
    for ev in events:
        real = _duration(ev.duration_type, ev.dots)
        alt = _duration(_PAIR[ev.duration_type], ev.dots)
        states = {(s + d, c or changed) for s, c in states for d, changed in ((real, False), (alt, True))
                  if s + d <= target}
    return (target, True) in states


def value_signs(events) -> Dict[int, str]:
    # Signos de valor por indice de evento segun el ejemplo 1-3 del Manual
    timed = [(i, ev) for i, ev in enumerate(events) if isinstance(ev, (Note, Chord, Rest))]
    if not timed or not _ambiguous([ev for _, ev in timed]):
        return {}
    signs: Dict[int, str] = {}
    previous = None
    for i, ev in timed:
        large = ev.duration_type in _LARGE
        if previous is None and not large:
            signs[i] = bt.SMALLER_VALUES
        elif previous is not None and large != previous:
            signs[i] = bt.VALUE_SEPARATION
        previous = large
    return signs


def _span(dtype: str, beats: int, beat_type: int) -> int:
    # Tramo que completa un grupo segun la regla 4-5; cero si la figura no se agrupa en ese compas
    if dtype == "32nd":
        return _UNITS["eighth"]
    if dtype != "16th" or beat_type == 16:
        return 0
    if beat_type == 8 and beats % 3 == 0:
        return 3 * _UNITS["eighth"]
    return _UNITS["quarter"]


def group_values(events, beats: int, beat_type: int):
    # Reglas 4-2 a 4-7: indices que se escriben como corchea y los que llevan signo de valor mayor
    shown, larger = set(), set()
    pos, starts = 0, []
    for ev in events:
        starts.append(pos)
        pos += _duration(ev.duration_type, ev.dots) if isinstance(ev, (Note, Chord, Rest)) else 0
    grouped = set()
    i = 0
    while i < len(events):
        ev = events[i]
        dtype = getattr(ev, "duration_type", "")
        span = _span(dtype, beats, beat_type) if isinstance(ev, (Note, Chord, Rest)) and not ev.dots else 0
        n = span // _UNITS[dtype] if span else 0
        group = events[i:i + n]
        ok = (n > 1 and len(group) == n and starts[i] % span == 0
              and all(isinstance(x, (Note, Chord)) and x.duration_type == dtype and not x.dots for x in group[1:])
              and not any(isinstance(x, (Note, Chord, Rest)) and x.duration_type == "eighth" for x in events[i + n:]))
        if ok:
            shown.update(range(i + 1, i + n))
            grouped.update(range(i, i + n))
            i += n
        else:
            i += 1
    if shown:
        for k, ev in enumerate(events[:-1]):
            if k in grouped or not isinstance(ev, (Note, Chord)) or ev.dots:
                continue
            span = _span(ev.duration_type, beats, beat_type)
            n = span // _UNITS[ev.duration_type] if span else 0
            run = events[k + 1:k + n]
            if n > 1 and len(run) == n - 1 and all(isinstance(x, (Note, Chord)) and x.duration_type == "eighth" and not x.dots for x in run):
                larger.add(k + 1)
    return shown, larger


class HandTranslator:
    def __init__(self, score: Score, hand: Hand, grouping: bool = False) -> None:
        self.hand = hand
        self.meter = (score.beats, score.beat_type)
        self.grouping = grouping
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
                   suppress_tie: bool = False, shown: str = "") -> str:
        out = []
        if note.slur_open:
            out.append(bt.SLUR_OPEN)

        out.append(self._accidental_cells(note))

        if force_octave:
            self.octave_state.observe(note)
            out.append(bt.OCTAVE_SIGN[note.octave])
        elif self.octave_state.needs_octave_sign(note):
            out.append(bt.OCTAVE_SIGN[note.octave])

        out.append(bt.note_cell(note.step, shown or note.duration_type))
        out.append(bt.DOT * note.dots)
        # la ligadura de expresion va antes que la de prolongacion
        if note.slur:
            out.append(bt.SLUR)
        if note.slur_close:
            out.append(bt.SLUR_CLOSE)
        if note.tie and not suppress_tie:
            out.append(bt.TIE)
        return "".join(out)

    def _emit_chord(self, chord: Chord, shown: str = "") -> str:
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
        out.append(self._emit_note(principal, suppress_tie=chord.tie, shown=shown))
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
        # Hasta tres compases se repite el silencio; desde cuatro va el numero de compases
        if count <= 3:
            return bt.REST["whole"] * count
        digits = "".join(bt.UPPER_DIGIT[int(d)] for d in str(count))
        return bt.NUMBER_SIGN + digits + bt.REST["whole"]

    def _emit_voice(self, events, force_first_octave: bool) -> str:
        parts: List[str] = []
        first = force_first_octave
        signs = value_signs(events)
        shown, larger = group_values(events, *self.meter) if self.grouping else (set(), set())
        for i, ev in enumerate(events):
            parts.append(signs.get(i, "") or (bt.LARGER_VALUES if i in larger else ""))
            as_eighth = "eighth" if i in shown else ""
            if isinstance(ev, MultiRest):
                parts.append(self._multi_rest(ev.count))
            elif isinstance(ev, Rest):
                parts.append(bt.REST[ev.duration_type] + bt.DOT * ev.dots)
            elif isinstance(ev, Chord):
                parts.append(self._emit_chord(ev, shown=as_eighth))
                first = False
            elif isinstance(ev, Note):
                parts.append(self._emit_note(ev, force_octave=first, shown=as_eighth))
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
        # measures_per_line debe coincidir con el del renderizador para saber donde empieza cada renglon
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
    # Silencio de redonda por compas callado y compases agrupados si callan ambas manos
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
                    merge_rests: bool = True, grouping: bool = False):
    # Devuelve los compases de cada mano; grouping aplica la agrupacion de la seccion IV del Manual
    if merge_rests:
        score = merge_rest_measures(score)
    rh = HandTranslator(score, score.right, grouping).translate(measures_per_line)
    lh = HandTranslator(score, score.left, grouping).translate(measures_per_line)
    return rh, lh
