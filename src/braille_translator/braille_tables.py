"""Tablas de simbolos de musicografia Braille.

Cada tabla referencia la regla correspondiente de docs/braille_rules_subset.md
y la seccion del Manual Simplificado de Musicografia Braille (ONCE, 2001).

Convencion de puntos: dot1=1, dot2=2, dot3=4, dot4=8, dot5=16, dot6=32.
El caracter Unicode Braille es chr(0x2800 + suma_de_puntos).
"""

def cell(*dots: int) -> str:
    """Construye un caracter Braille Unicode a partir de numeros de punto (1-6)."""
    value = 0
    for d in dots:
        value |= 1 << (d - 1)
    return chr(0x2800 + value)


NOTE_BASE = {
    "C": cell(1, 4, 5),      # Do
    "D": cell(1, 5),         # Re
    "E": cell(1, 2, 4),      # Mi
    "F": cell(1, 2, 4, 5),   # Fa
    "G": cell(1, 2, 5),      # Sol
    "A": cell(2, 4),         # La
    "B": cell(2, 4, 5),      # Si
}

# Puntos adicionales por grupo de duracion 
#   redonda/semicorchea -> +3+6 ; blanca/fusa -> +3 ; negra/semifusa -> +6 ;
#   corchea/garrapatea  -> nada
DURATION_EXTRA_DOTS = {
    "whole": (3, 6), "16th": (3, 6),
    "half": (3,), "32nd": (3,),
    "quarter": (6,), "64th": (6,),
    "eighth": (), "128th": (),
}


def note_cell(step: str, duration_type: str) -> str:
    """Regla 1-1: celda de nota = letra base + puntos de duracion."""
    base = NOTE_BASE[step]
    value = ord(base) - 0x2800
    for d in DURATION_EXTRA_DOTS[duration_type]:
        value |= 1 << (d - 1)
    return chr(0x2800 + value)


REST = {
    "whole": cell(1, 3, 4), "16th": cell(1, 3, 4),
    "half": cell(1, 3, 6), "32nd": cell(1, 3, 6),
    "quarter": cell(1, 2, 3, 6), "64th": cell(1, 2, 3, 6),
    "eighth": cell(1, 3, 4, 6), "128th": cell(1, 3, 4, 6),
}

DOT = cell(3)

OCTAVE_SIGN = {
    1: cell(4),
    2: cell(4, 5),
    3: cell(4, 5, 6),
    4: cell(5),
    5: cell(4, 6),
    6: cell(5, 6),
    7: cell(6),
}

ACCIDENTAL = {
    1: cell(1, 4, 6),    # sostenido
    -1: cell(1, 2, 6),   # bemol
    0: cell(1, 6),       # becuadro
    2: cell(1, 4, 6) + cell(1, 4, 6),    # doble sostenido
    -2: cell(1, 2, 6) + cell(1, 2, 6),   # doble bemol
}

INTERVAL = {
    2: cell(3, 4),
    3: cell(3, 4, 6),
    4: cell(3, 4, 5, 6),
    5: cell(3, 5),
    6: cell(3, 5, 6),
    7: cell(2, 5),
    8: cell(3, 6),
}

RIGHT_HAND = cell(4, 6) + cell(3, 4, 5)   # parte de mano derecha
LEFT_HAND = cell(4, 5, 6) + cell(3, 4, 5)  # parte de mano izquierda

BAR = "\u2800"                      # celda vacia = separador de compas
DOUBLE_BAR = cell(1, 2, 6) + cell(1, 3)          # doble barra (fin de seccion)
FINAL_BAR = cell(1, 2, 6) + cell(1, 3)           # barra final

TIE = cell(4) + cell(1, 4)

# Separan voces simultaneas dentro de un mismo compas y mano.
IN_ACCORD = cell(1, 2, 6) + cell(3, 4, 5)
PARTIAL_IN_ACCORD = cell(5) + cell(2)
MEASURE_DIVISION = cell(4, 6) + cell(1, 3)

NUMBER_SIGN = cell(3, 4, 5, 6)

UPPER_DIGIT = {
    1: cell(1), 2: cell(1, 2), 3: cell(1, 4), 4: cell(1, 4, 5), 5: cell(1, 5),
    6: cell(1, 2, 4), 7: cell(1, 2, 4, 5), 8: cell(1, 2, 5), 9: cell(2, 4),
    0: cell(2, 4, 5),
}

LOWER_DIGIT = {
    1: cell(2), 2: cell(2, 3), 3: cell(2, 5), 4: cell(2, 5, 6), 5: cell(2, 6),
    6: cell(2, 3, 5), 7: cell(2, 3, 5, 6), 8: cell(2, 3, 6), 9: cell(3, 5),
    0: cell(3, 5, 6),
}


def time_signature(beats: int, beat_type: int) -> str:
    return NUMBER_SIGN + UPPER_DIGIT[beats] + LOWER_DIGIT[beat_type]


BRAILLE_ASCII = (
    " a1b'k2l@cif/msp\"e3h9o6r^djg>ntq,*5<-u8v.%[$+x!&;:4\\0z7(_?w]#y)="
)


def unicode_to_brf(text: str) -> str:
    """Convierte una cadena de celdas Braille Unicode a Braille ASCII (BRF)."""
    out = []
    for ch in text:
        code = ord(ch)
        if 0x2800 <= code <= 0x283F:
            out.append(BRAILLE_ASCII[code - 0x2800])
        elif ch == "\n":
            out.append("\n")
        else:
            out.append(" ")
    return "".join(out)
