"""Exportador BRF 

Convierte el texto Braille Unicode al formato BRF (Braille ASCII), compatible
con impresoras Braille y lineas Braille. El formato BRF estandar
usa lineas de hasta 40 celdas y paginas de 25 lineas.
"""
from .braille_tables import unicode_to_brf

LINE_WIDTH = 40
LINES_PER_PAGE = 25


def export_brf(braille_text: str, path: str) -> None:
    ascii_text = unicode_to_brf(braille_text)

    wrapped_lines = []
    for line in ascii_text.split("\n"):
        if len(line) <= LINE_WIDTH:
            wrapped_lines.append(line)
        else:
            for i in range(0, len(line), LINE_WIDTH):
                wrapped_lines.append(line[i : i + LINE_WIDTH])

    with open(path, "w", encoding="ascii", newline="\r\n") as f:
        for i, line in enumerate(wrapped_lines):
            f.write(line + "\n")
            if (i + 1) % LINES_PER_PAGE == 0:
                f.write("\f")   # form feed = salto de pagina Braille
