"""Renderizador Bar-over-bar 

- Cada parrafo agrupa N compases, por defecto 4
- Linea de mano derecha arriba, mano izquierda debajo
- El primer signo de cada compas queda alineado verticalmente entre ambas
  manos, rellenando con celdas vacias la mano mas corta.
"""
from typing import List

from . import braille_tables as bt

EMPTY = "\u2800"   # celda Braille vacia

DEFAULT_MEASURES_PER_LINE = 4


def _pad(cells: str, width: int) -> str:
    return cells + EMPTY * (width - len(cells))


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
        for rh_m, lh_m in zip(rh_group, lh_group):
            width = max(len(rh_m), len(lh_m))
            padded_rh.append(_pad(rh_m, width))
            padded_lh.append(_pad(lh_m, width))

        is_last_group = start + measures_per_line >= n
        tail = bt.FINAL_BAR if is_last_group else ""

        lines.append(bt.RIGHT_HAND + EMPTY + (EMPTY.join(padded_rh)) + tail)
        lines.append(bt.LEFT_HAND + EMPTY + (EMPTY.join(padded_lh)) + tail)
        lines.append("")   # separador entre parrafos

    return "\n".join(lines).rstrip("\n")
