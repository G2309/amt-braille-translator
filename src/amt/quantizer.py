from typing import Dict, List, Optional, Sequence, Tuple

from braille_translator.model import Chord, Measure, Note, Rest, Score

from .events import MIDDLE_C_MIDI, NoteEvent, TranscriptionResult

TICKS_PER_QUARTER = 4   # grilla de semicorchea

# (ticks, duration_type, puntillos), de mayor a menor
_DURATIONS: Tuple[Tuple[int, str, int], ...] = (
    (16, "whole", 0),
    (12, "half", 1),
    (8, "half", 0),
    (6, "quarter", 1),
    (4, "quarter", 0),
    (3, "eighth", 1),
    (2, "eighth", 0),
    (1, "16th", 0),
)

_DURATION_TICKS = {(dtype, dots): size for size, dtype, dots in _DURATIONS}

_PITCH_CLASS = (
    ("C", 0), ("C", 1), ("D", 0), ("D", 1), ("E", 0), ("F", 0),
    ("F", 1), ("G", 0), ("G", 1), ("A", 0), ("A", 1), ("B", 0),
)


def midi_to_note(pitch: int) -> Tuple[str, int, int]:
    """MIDI -> (step, alter, octava Braille). Do central (60) es octava 4."""
    step, alter = _PITCH_CLASS[pitch % 12]
    return step, alter, pitch // 12 - 1


def largest_duration(ticks: int) -> Tuple[str, int]:
    """Mayor simbolo que cabe en ticks."""
    for size, dtype, dots in _DURATIONS:
        if size <= ticks:
            return dtype, dots
    return "16th", 0


def split_duration(ticks: int) -> List[Tuple[str, int]]:
    """Descompone ticks en simbolos sucesivos. Solo para silencios."""
    out = []
    while ticks > 0:
        for size, dtype, dots in _DURATIONS:
            if size <= ticks:
                out.append((dtype, dots))
                ticks -= size
                break
        else:
            break
    return out


def ticks_per_measure(beats: int, beat_type: int) -> int:
    return beats * TICKS_PER_QUARTER * 4 // beat_type


def _group_by_onset(notes: Sequence[NoteEvent], seconds_per_tick: float) -> Dict[int, List[Tuple[int, int]]]:
    """onset_tick -> [(midi_pitch, duracion_en_ticks)]"""
    groups: Dict[int, List[Tuple[int, int]]] = {}
    for ev in notes:
        onset = int(round(ev.onset_s / seconds_per_tick))
        offset = int(round(ev.offset_s / seconds_per_tick))
        groups.setdefault(onset, []).append((ev.midi_pitch, max(1, offset - onset)))
    return groups


def _hand_events(
    notes: Sequence[NoteEvent],
    seconds_per_tick: float,
    total_ticks: int,
    per_measure: int,
) -> List[Measure]:
    groups = _group_by_onset(notes, seconds_per_tick)
    onsets = sorted(groups)

    measures = [Measure(i + 1) for i in range(max(1, -(-total_ticks // per_measure)))]

    def emit(start: int, length: int, pitches: Optional[List[int]]) -> None:
        """Coloca un evento, partiendolo en figuras representables.

        Los trozos de una misma nota quedan unidos por ligadura de
        prolongacion, asi que puede cruzar la barra sin perder duracion.
        """
        while length > 0:
            index = start // per_measure
            if index >= len(measures):
                return
            room = per_measure - (start % per_measure)
            if pitches is None:
                chunk = min(length, room)
                for dtype, dots in split_duration(chunk):
                    measures[index].events.append(Rest(dtype, dots))
                start += chunk
                length -= chunk
                continue

            dtype, dots = largest_duration(min(length, room))
            used = _DURATION_TICKS[(dtype, dots)]
            tied = length - used > 0
            built = [_build_note(p, dtype, dots, tie=tied) for p in pitches]
            if len(built) == 1:
                measures[index].events.append(built[0])
            else:
                measures[index].events.append(Chord(built, dtype, dots, tie=tied))
            start += used
            length -= used

    cursor = 0
    for i, onset in enumerate(onsets):
        if onset < cursor:
            continue          # solape: ya cubierto por el evento anterior
        if onset > cursor:
            emit(cursor, onset - cursor, None)
        members = groups[onset]
        length = min(d for _, d in members)
        next_onset = onsets[i + 1] if i + 1 < len(onsets) else total_ticks
        if next_onset > onset:
            length = min(length, next_onset - onset)
        length = max(1, length)
        emit(onset, length, [p for p, _ in members])
        cursor = onset + length

    if cursor < total_ticks:
        emit(cursor, total_ticks - cursor, None)

    for m in measures:
        if not m.events:
            m.events.append(Rest("whole", 0))
    return measures


def _build_note(pitch: int, duration_type: str, dots: int, tie: bool = False) -> Note:
    step, alter, octave = midi_to_note(pitch)
    return Note(
        step=step,
        octave=max(1, min(7, octave)),
        duration_type=duration_type,
        alter=alter,
        dots=dots,
        tie=tie,
    )


def quantize(
    result: TranscriptionResult,
    tempo_bpm: float = 60.0,
    beats: int = 4,
    beat_type: int = 4,
    fifths: int = 0,
    split_pitch: int = MIDDLE_C_MIDI,
    title: str = "",
) -> Score:
    if tempo_bpm <= 0:
        raise ValueError("tempo_bpm debe ser positivo")

    seconds_per_tick = 60.0 / (tempo_bpm * TICKS_PER_QUARTER)
    per_measure = ticks_per_measure(beats, beat_type)

    right_notes, left_notes = result.split_hands(split_pitch)
    end_s = max((n.offset_s for n in result.notes), default=0.0)
    total_ticks = int(round(end_s / seconds_per_tick))
    total_ticks = max(per_measure, -(-total_ticks // per_measure) * per_measure)

    score = Score(title=title, beats=beats, beat_type=beat_type, fifths=fifths)
    score.right.measures = _hand_events(right_notes, seconds_per_tick, total_ticks, per_measure)
    score.left.measures = _hand_events(left_notes, seconds_per_tick, total_ticks, per_measure)
    return score
