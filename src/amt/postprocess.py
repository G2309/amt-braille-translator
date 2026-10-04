# Heuristicas ligeras sobre las notas transcritas, antes de cuantizar
from dataclasses import replace
from typing import List, Sequence, Tuple

from .events import NoteEvent, TranscriptionResult

HARMONIC_INTERVALS = (12, 19, 24)


def drop_octave_ghosts(result: TranscriptionResult, window_s: float = 0.03,
                       ratio: float = 0.7) -> TranscriptionResult:
    # Quita la nota que suena un armonico arriba de otra casi al mismo tiempo y con menos fuerza
    notes = result.sorted_notes()
    keep = []
    for i, n in enumerate(notes):
        ghost = False
        for m in notes[max(0, i - 16): i + 16]:
            if (n.midi_pitch - m.midi_pitch in HARMONIC_INTERVALS
                    and abs(n.onset_s - m.onset_s) <= window_s
                    and n.velocity <= ratio * m.velocity):
                ghost = True
                break
        if not ghost:
            keep.append(n)
    return replace(result, notes=keep)


def collapse_trills(result: TranscriptionResult, max_ioi_s: float = 0.09,
                    min_notes: int = 4) -> TranscriptionResult:
    # Un trino o mordente largo se escribe como su nota principal con la duracion de todo el adorno
    notes = result.sorted_notes()
    used = [False] * len(notes)
    out: List[NoteEvent] = []
    for i, first in enumerate(notes):
        if used[i]:
            continue
        chain = [i]
        other = None
        j = i + 1
        while j < len(notes) and notes[j].onset_s - notes[chain[-1]].onset_s <= max_ioi_s:
            cand, last = notes[j], notes[chain[-1]]
            target = first.midi_pitch if len(chain) % 2 == 0 else other
            if not used[j] and cand.onset_s > last.onset_s and (
                    cand.midi_pitch == target if target is not None
                    else 0 < abs(cand.midi_pitch - first.midi_pitch) <= 2):
                other = cand.midi_pitch if other is None else other
                chain.append(j)
            j += 1
        if len(chain) >= min_notes:
            for k in chain:
                used[k] = True
            end = max(notes[k].offset_s for k in chain)
            out.append(replace(first, offset_s=end))
        else:
            used[i] = True
            out.append(first)
    return replace(result, notes=out)


def split_hands_by_continuity(notes: Sequence[NoteEvent], chord_s: float = 0.03,
                              right_start: float = 67.0, left_start: float = 50.0,
                              memory: float = 0.3) -> Tuple[List[NoteEvent], List[NoteEvent]]:
    # Reparte cada acorde por el corte que deja a cada mano mas cerca de su registro reciente
    ordered = sorted(notes, key=lambda n: (n.onset_s, n.midi_pitch))
    right, left = [], []
    centers = [left_start, right_start]
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j].onset_s - ordered[i].onset_s <= chord_s:
            j += 1
        group = sorted(ordered[i:j], key=lambda n: n.midi_pitch)
        best, cut = None, 0
        for k in range(len(group) + 1):
            cost = sum(abs(n.midi_pitch - centers[0]) for n in group[:k])
            cost += sum(abs(n.midi_pitch - centers[1]) for n in group[k:])
            if best is None or cost < best:
                best, cut = cost, k
        for side, part in ((0, group[:cut]), (1, group[cut:])):
            if part:
                mean = sum(n.midi_pitch for n in part) / len(part)
                centers[side] += memory * (mean - centers[side])
        left += group[:cut]
        right += group[cut:]
        i = j
    return right, left


def split_voices(notes: Sequence[NoteEvent], chord_s: float = 0.03, overlap_s: float = 0.05,
                 dormant_s: float = 0.5) -> Tuple[List[NoteEvent], List[NoteEvent]]:
    # Separa una mano en voz superior e inferior segun que voz esta libre y cual queda mas cerca en altura
    ordered = sorted(notes, key=lambda n: (n.onset_s, n.midi_pitch))
    voices: Tuple[List[NoteEvent], List[NoteEvent]] = ([], [])
    last_pitch = [None, None]
    last_end = [float("-inf"), float("-inf")]
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j].onset_s - ordered[i].onset_s <= chord_s:
            j += 1
        group = sorted(ordered[i:j], key=lambda n: n.midi_pitch)
        t = group[0].onset_s
        if len(group) > 1:
            parts = ((0, group[-1:]), (1, group[:-1]))
        else:
            free = [last_end[v] <= t + overlap_s for v in (0, 1)]
            pitch = group[0].midi_pitch
            if free[0] and (not free[1] or last_end[1] < t - dormant_s or last_pitch[1] is None):
                target = 0
            elif free[1] and not free[0]:
                target = 1
            else:
                target = min((0, 1), key=lambda v: abs(pitch - last_pitch[v]) if last_pitch[v] is not None else 99)
            parts = ((target, group),)
        for v, part in parts:
            voices[v].extend(part)
            last_pitch[v] = part[-1].midi_pitch if v == 0 else part[0].midi_pitch
            last_end[v] = max(n.offset_s for n in part)
        i = j
    return voices


def split_hands_viterbi(notes: Sequence[NoteEvent], chord_s: float = 0.03, memory: float = 0.2,
                        span: int = 16, span_weight: float = 4.0, beam: int = 8,
                        right_start: float = 67.0, left_start: float = 50.0) -> Tuple[List[NoteEvent], List[NoteEvent]]:
    # Igual que la continuidad, pero el corte de cada acorde se elige mirando toda la obra con busqueda en haz
    ordered = sorted(notes, key=lambda n: (n.onset_s, n.midi_pitch))
    groups: List[List[NoteEvent]] = []
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j].onset_s - ordered[i].onset_s <= chord_s:
            j += 1
        groups.append(sorted(ordered[i:j], key=lambda n: n.midi_pitch))
        i = j

    def stretch(part: List[NoteEvent]) -> float:
        return max(0, part[-1].midi_pitch - part[0].midi_pitch - span) if part else 0

    # Cada hipotesis guarda costo, registro suavizado de cada mano y la lista de cortes
    hyps = [(0.0, left_start, right_start, [])]
    for group in groups:
        nxt = []
        for cost, lc, rc, cuts in hyps:
            for cut in range(len(group) + 1):
                left, right = group[:cut], group[cut:]
                c = cost + sum(abs(n.midi_pitch - lc) for n in left) + sum(abs(n.midi_pitch - rc) for n in right)
                c += span_weight * (stretch(left) + stretch(right))
                nl = lc + memory * (sum(n.midi_pitch for n in left) / len(left) - lc) if left else lc
                nr = rc + memory * (sum(n.midi_pitch for n in right) / len(right) - rc) if right else rc
                nxt.append((c, nl, nr, cuts + [cut]))
        nxt.sort(key=lambda h: h[0])
        hyps = nxt[:beam]
    cuts = hyps[0][3] if hyps else []
    right_out: List[NoteEvent] = []
    left_out: List[NoteEvent] = []
    for group, cut in zip(groups, cuts):
        left_out += group[:cut]
        right_out += group[cut:]
    return right_out, left_out
