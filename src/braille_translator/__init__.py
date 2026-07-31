"""braille_translator — Modulo determinista de traduccion a musicografia Braille.

Pipeline: MusicXML -> AST -> FSM/Traductor -> Bar-over-bar -> BRF

Actividades del Cronograma cubiertas: A3.1 (parcial, sin cuantizacion de audio
aun), A3.2 (FSM), A3.3 (AST), A3.4 (renderizador), A3.5 (exportador BRF).
Historias de usuario: US-02, US-07, US-08, US-09, US-10, US-11 (parcial).
"""
from . import braille_tables
from .brf_exporter import export_brf
from .model import Chord, Hand, Measure, Note, Rest, Score
from .musicxml_parser import parse_musicxml
from .renderer import DEFAULT_MEASURES_PER_LINE, render_bar_over_bar
from .translator import translate_score


def musicxml_to_brf(
    input_path: str,
    output_path: str,
    measures_per_line: int = DEFAULT_MEASURES_PER_LINE,
) -> str:
    """Pipeline completo de archivo MusicXML a archivo BRF.

    Devuelve el texto Braille Unicode generado (util para inspeccion y pruebas).
    """
    score = parse_musicxml(input_path)
    rh, lh = translate_score(score, measures_per_line)
    header = braille_tables.time_signature(score.beats, score.beat_type)
    braille = render_bar_over_bar(rh, lh, measures_per_line, header=header)
    export_brf(braille, output_path)
    return braille


__all__ = [
    "Score", "Hand", "Measure", "Note", "Chord", "Rest",
    "parse_musicxml", "translate_score", "render_bar_over_bar",
    "export_brf", "musicxml_to_brf", "braille_tables",
]
