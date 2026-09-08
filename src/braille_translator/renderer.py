"""Renderizador Bar-over-bar (compas sobre compas, Seccion XIV.C.1)

- Regla 14-16: una linea por pentagrama; en piano, paralela de dos lineas.
- Regla 14-17 / 14-20: el primer signo de cada compas queda alineado
  verticalmente entre ambas manos.
- Regla 14-18: los tres primeros espacios de cada linea llevan el
  indicativo de parte (signo de mano + celda en blanco).
- Regla 14-22: el espacio sobrante de un compas mas corto se rellena con
  una linea guia de punto 3, innecesaria en el ultimo compas de la paralela.
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
                # Regla 14-22: sin linea guia en el ultimo compas de la paralela
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
