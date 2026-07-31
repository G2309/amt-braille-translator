"""Pipeline completo audio -> BRF.

Une el modulo AMT con el traductor Braille. Vive fuera de ambos para que
ninguno dependa del otro.
"""
from typing import Optional

from amt import AMTTranscriber, TranscriptionResult, quantize
from braille_translator import braille_tables, export_brf, render_bar_over_bar, translate_score
from braille_translator.renderer import DEFAULT_MEASURES_PER_LINE


def result_to_brf(
    result: TranscriptionResult,
    output_path: Optional[str] = None,
    tempo_bpm: float = 60.0,
    beats: int = 4,
    beat_type: int = 4,
    fifths: int = 0,
    measures_per_line: int = DEFAULT_MEASURES_PER_LINE,
) -> str:
    score = quantize(result, tempo_bpm=tempo_bpm, beats=beats, beat_type=beat_type, fifths=fifths)
    rh, lh = translate_score(score, measures_per_line)
    header = braille_tables.time_signature(score.beats, score.beat_type)
    braille = render_bar_over_bar(rh, lh, measures_per_line, header=header)
    if output_path:
        export_brf(braille, output_path)
    return braille


def audio_to_brf(
    audio_path: str,
    output_path: str,
    tempo_bpm: float = 60.0,
    beats: int = 4,
    beat_type: int = 4,
    fifths: int = 0,
    measures_per_line: int = DEFAULT_MEASURES_PER_LINE,
    transcriber: Optional[AMTTranscriber] = None,
) -> str:
    result = (transcriber or AMTTranscriber()).transcribe(audio_path)
    return result_to_brf(
        result,
        output_path=output_path,
        tempo_bpm=tempo_bpm,
        beats=beats,
        beat_type=beat_type,
        fifths=fifths,
        measures_per_line=measures_per_line,
    )
