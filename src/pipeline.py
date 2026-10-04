# Pipeline completo de audio a BRF; vive fuera de AMT y del traductor para que ninguno dependa del otro
from typing import Optional

from amt import AMTTranscriber, TranscriptionResult, quantize
from amt.beats import beat_unit_quarters, follow_tempo
from amt.postprocess import drop_octave_ghosts, split_hands_viterbi
from braille_translator import braille_tables, export_brf, render_bar_over_bar, translate_score
from braille_translator.renderer import DEFAULT_MEASURES_PER_LINE

# Valores elegidos con la particion de desarrollo de las Goldberg
DEFAULT_LEGATO = 0.75
GHOST_RATIO = 1.0
GHOST_WINDOW_S = 0.05
HAND_MEMORY = 0.2
HAND_SPAN_WEIGHT = 4.0
VOICE_THRESHOLD = 0.5
BEAT_DROP_PENALTY = 2.0


def result_to_brf(
    result: TranscriptionResult,
    output_path: Optional[str] = None,
    tempo_bpm: float = 60.0,
    beats: int = 4,
    beat_type: int = 4,
    fifths: int = 0,
    measures_per_line: int = DEFAULT_MEASURES_PER_LINE,
    legato: float = DEFAULT_LEGATO,
    cleanup: bool = True,
    voices: bool = False,
    track: bool = True,
    grouping: bool = True,
    slurs: bool = False,
) -> str:
    # cleanup quita armonicos y reparte manos; voices (opcional) usa in-accord en compases polifonicos; track sigue el pulso
    if cleanup:
        result = drop_octave_ghosts(result, window_s=GHOST_WINDOW_S, ratio=GHOST_RATIO)
    if track and result.notes:
        per_bar = int(round(beats * 4 / beat_type / beat_unit_quarters(beat_type)))
        result = follow_tempo(result, tempo_bpm, beat_type, beats_per_bar=per_bar, drop_penalty=BEAT_DROP_PENALTY)
        tempo_bpm = 60.0
    hands = split_hands_viterbi(result.notes, memory=HAND_MEMORY, span_weight=HAND_SPAN_WEIGHT, beam=1) if cleanup else None
    # slurs infiere ligaduras del legato; queda apagado porque en desarrollo bajo el BSA
    score = quantize(result, tempo_bpm=tempo_bpm, beats=beats, beat_type=beat_type, fifths=fifths, legato=legato,
                     hands=hands, voices=("right", "left") if voices else (), voice_threshold=VOICE_THRESHOLD,
                     slur_ratio=0.0 if slurs else None)
    rh, lh = translate_score(score, measures_per_line, grouping=grouping)
    # armadura y compas van juntos en la cabecera
    header = braille_tables.key_signature(score.fifths) + braille_tables.time_signature(
        score.beats, score.beat_type
    )
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
    legato: float = DEFAULT_LEGATO,
    cleanup: bool = True,
    voices: bool = False,
    track: bool = True,
    grouping: bool = True,
    slurs: bool = False,
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
        legato=legato,
        cleanup=cleanup,
        voices=voices,
        track=track,
        grouping=grouping,
        slurs=slurs,
    )
