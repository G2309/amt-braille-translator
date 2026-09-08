"""Renderizador compas sobre compas (bar over bar).

Una linea por pentagrama, que en piano forman la paralela de dos. El primer
signo de cada compas queda alineado en vertical entre ambas manos, los tres
primeros espacios llevan el signo de mano y el hueco que deja el compas mas
corto se rellena con una linea guia de punto 3, salvo en el ultimo de la
paralela.
"""
from typing import List

from . import braille_tables as bt

EMPTY = "⠀"   # celda Braille vacia

DEFAULT_MEASURES_PER_LINE = 4


def _pad(cells: str, width: int, filler: str) -> str:
    return cells + filler * (width - len(cells))


def render_bar_over_bar(
    rh_measures: List[str],
    lh_measures: List[str],
    measures_per_line: int = DEFAULT_MEASURES_PER_LINE,
    header: str = "",
) -> str:
    assert len(rh_measures) == len(lh_measures), "Ambas manos deben tener el mismo numero de compases"

    lines: List[str] = []
    if header:
        lines.append(header)
        lines.append("")

    n = len(rh_measures)
    for start in range(0, n, measures_per_line):
        rh_group = rh_measures[start : start + measures_per_line]
        lh_group = lh_measures[start : start + measures_per_line]

        padded_rh, padded_lh = [], []
        last = len(rh_group) - 1
        for i, (rh_m, lh_m) in enumerate(zip(rh_group, lh_group)):
            if i == last:
                # el ultimo compas de la paralela no necesita linea guia
                padded_rh.append(rh_m)
                padded_lh.append(lh_m)
                continue
            width = max(len(rh_m), len(lh_m))
            padded_rh.append(_pad(rh_m, width, bt.DOT))
            padded_lh.append(_pad(lh_m, width, bt.DOT))

        is_last_group = start + measures_per_line >= n
        tail = bt.FINAL_BAR if is_last_group else ""

        lines.append(bt.RIGHT_HAND + EMPTY + (EMPTY.join(padded_rh)) + tail)
        lines.append(bt.LEFT_HAND + EMPTY + (EMPTY.join(padded_lh)) + tail)
        lines.append("")   # separador entre paralelas

    return "\n".join(lines).rstrip("\n")
