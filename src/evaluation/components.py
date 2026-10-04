# Desglose del BSA en alturas, ritmo y fraseo, leyendo el Braille como lo haria un lector
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Sequence, Tuple

from braille_translator import braille_tables as bt

from .bsa import classify_cells, compute_bsa
from .reference import clean
from .reference_eval import MAX_CELLS, merge

STEPS = "CDEFGAB"
_BASE = {ord(v) - 0x2800: k for k, v in bt.NOTE_BASE.items()}
_OCTAVE = {v: k for k, v in bt.OCTAVE_SIGN.items()}
_INTERVAL = {v: k for k, v in bt.INTERVAL.items()}
_VALUE_DOTS = 0x24


def read_pitches(cells: str, hand: str) -> List[Tuple[int, str]]:
    # Altura diatonica absoluta de cada nota e intervalo, aplicando las reglas de octava del Manual
    out: List[Tuple[int, str]] = []
    prev = principal = None
    forced = None
    for c, kind in classify_cells(cells):
        if kind == "octavas" and c in _OCTAVE:
            forced = _OCTAVE[c]
        elif kind == "in_accords":
            prev = None
        elif kind == "intervalos" and c in _INTERVAL and principal is not None:
            step = _INTERVAL[c] - 1
            pitch = principal - step if hand == "right" else principal + step
            if forced is not None:
                pitch, forced = forced * 7 + pitch % 7, None
            out.append((pitch, c))
        elif kind == "notas" and (ord(c) - 0x2800) & ~_VALUE_DOTS in _BASE:
            step = STEPS.index(_BASE[(ord(c) - 0x2800) & ~_VALUE_DOTS])
            if forced is not None or prev is None:
                pitch = (forced if forced is not None else 4) * 7 + step
            else:
                # Sin signo la nota queda a tercera o menos, o a cuarta o quinta dentro de la misma octava
                candidates = [o * 7 + step for o in range(prev // 7 - 1, prev // 7 + 2)]
                near = [p for p in candidates if abs(p - prev) <= 2]
                same = [p for p in candidates if p // 7 == prev // 7 and abs(p - prev) <= 4]
                pitch = near[0] if near else same[0] if same else min(candidates, key=lambda p: abs(p - prev))
            forced = None
            out.append((pitch, c))
            prev = principal = pitch
    return out


def pitch_and_rhythm(reference: Tuple[str, str], generated: Tuple[str, str]) -> Tuple[float, float]:
    # Alturas acertadas tras alinear cada mano, y de ellas cuantas tienen ademas la figura correcta
    matched = total = same_value = 0
    for ref, gen, hand in ((reference[0], generated[0], "right"), (reference[1], generated[1], "left")):
        a, b = read_pitches(ref, hand), read_pitches(gen, hand)
        blocks = SequenceMatcher(None, [x[0] for x in a], [x[0] for x in b], autojunk=False).get_matching_blocks()
        matched += sum(m.size for m in blocks)
        total += max(len(a), len(b))
        same_value += sum(1 for m in blocks for k in range(m.size) if a[m.a + k][1] == b[m.b + k][1])
    return matched / max(total, 1), same_value / max(matched, 1)


def note_f1_by_measure(reference: Sequence[Tuple[str, str]], generated: Sequence[Tuple[str, str]],
                       slack: int = 1) -> float:
    # F1 de alturas por mano y compas sin importar el orden ni la figura, tolerando un compas de corrimiento
    def bags(m: Tuple[str, str]) -> Tuple[Counter, Counter]:
        return Counter(p for p, _ in read_pitches(m[0], "right")), Counter(p for p, _ in read_pitches(m[1], "left"))
    ref = [bags(m) for m in reference]
    gen = [bags(m) for m in generated]
    hits = 0
    for k, (gr, gl) in enumerate(gen):
        hits += max((sum((gr & ref[j][0]).values()) + sum((gl & ref[j][1]).values())
                     for j in range(k - slack, k + slack + 1) if 0 <= j < len(ref)), default=0)
    n_gen = sum(sum((r + l).values()) for r, l in gen)
    n_ref = sum(sum((r + l).values()) for r, l in ref)
    precision, recall = hits / max(n_gen, 1), hits / max(n_ref, 1)
    return 2 * precision * recall / max(precision + recall, 1e-9)


def strip_phrasing(cells: str) -> str:
    # Quita las ligaduras de expresion, que el audio no transmite; conserva las de prolongacion
    cells = cells.replace(bt.SLUR_OPEN, "").replace(bt.SLUR_CLOSE, "")
    out, k = [], 0
    while k < len(cells):
        if cells.startswith(bt.TIE, k) or cells.startswith(bt.CHORD_TIE, k):
            out.append(cells[k:k + 2])
            k += 2
            continue
        if cells[k] != bt.SLUR:
            out.append(cells[k])
        k += 1
    return "".join(out)


@dataclass
class Components:
    bsa: float
    bsa_without_phrasing: float
    note_f1: float
    pitch: float
    rhythm: float


def components(evaluation) -> Components:
    # Desglose de una evaluacion de pieza hecha con evaluation.reference_eval.evaluate_piece
    ref = evaluation.reference
    hyp_r, hyp_l = ("".join(x) for x in evaluation.hyp_measures)
    without = merge(compute_bsa(strip_phrasing(ref.right), strip_phrasing(hyp_r), MAX_CELLS),
                    compute_bsa(strip_phrasing(ref.left), strip_phrasing(hyp_l), MAX_CELLS))
    ref_measures = [(clean(m.right, Counter()), clean(m.left, Counter())) for m in ref.played]
    pitch, rhythm = pitch_and_rhythm((ref.right, ref.left), (hyp_r, hyp_l))
    return Components(
        bsa=evaluation.both.bsa,
        bsa_without_phrasing=without.bsa,
        note_f1=note_f1_by_measure(ref_measures, list(zip(*evaluation.hyp_measures))),
        pitch=pitch,
        rhythm=rhythm,
    )
