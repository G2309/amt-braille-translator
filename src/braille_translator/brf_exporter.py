"""Exportador BRF

Convierte el texto Braille Unicode al formato BRF (Braille ASCII), compatible
con impresoras Braille y lineas Braille. El formato BRF estandar
usa lineas de hasta 40 celdas y paginas de 25 lineas.
"""
from typing import List

from .braille_tables import unicode_to_brf

LINE_WIDTH = 40
LINES_PER_PAGE = 25
RUNOVER_INDENT = 2


def wrap_line(line: str, width: int = LINE_WIDTH, indent: int = RUNOVER_INDENT) -> List[str]:
    """Parte en el ultimo espacio que quepa, para no cortar un compas a la mitad.

    Las lineas de continuacion van sangradas. Si un compas es mas largo que el
    ancho disponible se corta duro, que es preferible a no terminar nunca.
    """
    if len(line) <= width:
        return [line]

    out: List[str] = []
    prefix = ""
    rest = line
    while len(rest) > width - len(prefix):
        limit = width - len(prefix)
        cut = rest.rfind(" ", 0, limit + 1)
        if cut <= 0:
            cut = limit
        out.append(prefix + rest[:cut].rstrip())
        rest = rest[cut:].lstrip(" ")
        prefix = " " * indent
    if rest:
        out.append(prefix + rest)
    return out


def export_brf(braille_text: str, path: str) -> None:
    ascii_text = unicode_to_brf(braille_text)

    wrapped: List[str] = []
    for line in ascii_text.split("\n"):
        wrapped.extend(wrap_line(line))

    with open(path, "w", encoding="ascii", newline="\r\n") as f:
        for i, line in enumerate(wrapped):
            f.write(line + "\n")
            if (i + 1) % LINES_PER_PAGE == 0:
                f.write("\f")   # form feed = salto de pagina Braille
