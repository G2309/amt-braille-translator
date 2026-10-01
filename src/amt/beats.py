# Seguimiento simbolico del pulso para que las barras no se corran cuando el interprete cambia el tempo
import math
from typing import List, Sequence

from .events import NoteEvent, TranscriptionResult

BASS_PITCH = 55


def beat_unit_quarters(beat_type: int) -> float:
    # Negra en compases de x/2 y x/4, corchea en x/8 y x/16
    return 0.5 if beat_type >= 8 else 1.0


def onset_envelope(notes: Sequence[NoteEvent], hop_s: float, frames: int) -> List[float]:
    # Fuerza de ataque por cuadro, con mas peso en el bajo y suavizada con una gaussiana corta
    raw = [0.0] * frames
    for n in notes:
        k = int(round(n.onset_s / hop_s))
        if 0 <= k < frames:
            raw[k] += n.velocity / 127.0 * (1.5 if n.midi_pitch < BASS_PITCH else 1.0)
    kernel = [math.exp(-0.5 * (d / 1.5) ** 2) for d in range(-3, 4)]
    out = [0.0] * frames
    for k, v in enumerate(raw):
        if v:
            for d, w in enumerate(kernel, start=-3):
                if 0 <= k + d < frames:
                    out[k + d] += v * w
    return out


def track_beats(notes: Sequence[NoteEvent], period_s: float, alpha: float = 100.0,
                local: float = 0.7, hop_s: float = 0.01) -> List[float]:
    # Programacion dinamica que premia caer en ataques y castiga cambiar el intervalo; alpha y local salen de desarrollo
    if not notes:
        return [0.0, period_s]
    # El primer pulso se ancla en el primer ataque
    start = min(n.onset_s for n in notes)
    shifted = [NoteEvent(n.onset_s - start, n.offset_s - start, n.midi_pitch, n.velocity) for n in notes]
    end = max(n.onset_s for n in shifted) + period_s
    frames = int(end / hop_s) + 1
    env = onset_envelope(shifted, hop_s, frames)
    target = period_s / hop_s
    lo_f, hi_f = 1.5 * target, 0.6 * target
    score = [-math.inf] * frames
    prev = [-1] * frames
    gap = [target] * frames
    score[0] = env[0]
    for t in range(1, frames):
        best, arg, arg_gap = -math.inf, -1, target
        for tau in range(max(0, int(t - lo_f)), int(t - hi_f) + 1):
            if score[tau] == -math.inf:
                continue
            d = t - tau
            ref = local * gap[tau] + (1 - local) * target
            c = score[tau] - alpha * math.log(d / ref) ** 2
            if c > best:
                best, arg, arg_gap = c, tau, d
        if arg >= 0:
            score[t], prev[t], gap[t] = best + env[t], arg, arg_gap
    tail = int((end - 2 * period_s) / hop_s)
    last = max(range(max(0, tail), frames), key=lambda k: score[k])
    path = [last]
    while prev[path[-1]] >= 0:
        path.append(prev[path[-1]])
    return [start + k * hop_s for k in reversed(path)]


def warp_to_score(result: TranscriptionResult, beats: Sequence[float], unit_quarters: float,
                  origin_quarters: float = 0.0) -> TranscriptionResult:
    # Lleva cada tiempo al dominio de partitura, donde un segundo es una negra; el primer pulso cae en origin_quarters
    if len(beats) < 2:
        return result

    def warp(t: float) -> float:
        return origin_quarters + _beat_position(t)

    def _beat_position(t: float) -> float:
        if t >= beats[-1]:
            return (len(beats) - 1 + (t - beats[-1]) / (beats[-1] - beats[-2])) * unit_quarters
        if t <= beats[0]:
            return (t - beats[0]) / (beats[1] - beats[0]) * unit_quarters
        lo, hi = 0, len(beats) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if beats[mid] <= t:
                lo = mid
            else:
                hi = mid
        return (lo + (t - beats[lo]) / (beats[hi] - beats[lo])) * unit_quarters

    notes = []
    for n in result.notes:
        on = warp(n.onset_s)
        notes.append(NoteEvent(on, max(warp(n.offset_s), on + 1e-3), n.midi_pitch, n.velocity))
    pedals = [type(p)(warp(p.onset_s), max(warp(p.offset_s), warp(p.onset_s))) for p in result.pedals]
    return TranscriptionResult(notes=notes, pedals=pedals, duration_s=warp(result.duration_s),
                               source=result.source, model_name=result.model_name)


def follow_tempo(result: TranscriptionResult, tempo_bpm: float, beat_type: int,
                 **kwargs) -> TranscriptionResult:
    # Sigue el pulso desde el tempo indicado y devuelve las notas en tiempo de partitura a 60 negras por minuto
    unit = beat_unit_quarters(beat_type)
    beats = track_beats(result.notes, unit * 60.0 / tempo_bpm, **kwargs)
    return warp_to_score(result, beats, unit, origin_quarters=beats[0] * tempo_bpm / 60.0)
