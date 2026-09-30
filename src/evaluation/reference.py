"""Lectura de una referencia Braille de piano en formato compas sobre compas.

La referencia es un BRF hecho por un transcriptor: cada paralela lleva el numero
de compas en el margen, la parte de mano derecha y la de mano izquierda en lineas
seguidas, y un compas largo sigue en lineas sangradas sin signo de mano. Este
modulo la separa en piezas, lee armadura y compas del encabezado de cada pieza,
expande las repeticiones como las toca el interprete y quita los signos que
quedan fuera del subset de 28 reglas, para compararla contra la salida del
sistema con el BSA.
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from braille_translator import braille_tables as bt

from .bsa import UNKNOWN, classify_cells

_HAND_LINE = re.compile(r"^\s*([a-j]*)\s*([._])>(.*)$")
_PAGE_NUMBER = re.compile(r'^\s*"?\d?#[a-j]+\s*$')
_TITLE = re.compile(r"^\s+(aria4|v>i,n #[a-j]+4)\s*$")
_SIGNATURE = re.compile(r"(?:^|\s)([%<*]*)(#[a-j]+[0-9]+|[._]c)\s*$")

_UPPER = {c: i for i, c in enumerate("jabcdefghi")}
_LOWER = {c: i for i, c in enumerate("0123456789")}

BEGIN_REPEAT = "<7"
END_REPEAT = "<2"
VOLTA = re.compile(r"#([12])")

# Signos de la referencia que el sistema no escribe: repeticiones y casillas
# de volta (ya usadas al expandir) y ornamentos o articulaciones de una celda
# que el clasificador no reconoce.
_STRIPPED_TOKENS = (BEGIN_REPEAT, END_REPEAT, "<1", "#1", "#2")


@dataclass
class Measure:
    number: int
    right: str = ""
    left: str = ""

    def _head(self) -> str:
        return self.right[:6]

    @property
    def begins_repeat(self) -> bool:
        return BEGIN_REPEAT in self._head()

    @property
    def ends_repeat(self) -> bool:
        return END_REPEAT in self.right or END_REPEAT in self.left

    @property
    def volta(self) -> Optional[int]:
        m = VOLTA.search(self._head())
        return int(m.group(1)) if m else None


@dataclass
class Piece:
    index: int
    title: str
    fifths: int = 0
    beats: int = 4
    beat_type: int = 4
    measures: List[Measure] = field(default_factory=list)

    @property
    def has_pickup(self) -> bool:
        return bool(self.measures) and self.measures[0].number == 0

    @property
    def quarters_per_measure(self) -> float:
        return self.beats * 4 / self.beat_type


def _number(letters: str) -> int:
    return int("".join(str(_UPPER[c]) for c in letters)) if letters else 0


def parse_signature(token: str) -> Tuple[int, int, int]:
    """Armadura y compas de un encabezado como %#c4, <<#ab8, %.c o %_c."""
    m = _SIGNATURE.search(token)
    if not m:
        raise ValueError(f"encabezado sin armadura ni compas: {token!r}")
    accidentals, time = m.groups()
    fifths = accidentals.count("%") - accidentals.count("<")
    if time == ".c":
        return fifths, 4, 4
    if time == "_c":
        return fifths, 2, 2
    upper = re.match(r"#([a-j]+)", time).group(1)
    lower = time[1 + len(upper):]
    return fifths, _number(upper), int("".join(str(_LOWER[c]) for c in lower))


_GUIDE_FILL = re.compile(r"'{2,}$")


_TIME_ONLY = re.compile(r"^[%<*]*(#[a-j]+[0-9]+|[._]c)$")


def _segments(content: str) -> List[str]:
    """Compases de una linea.

    Los separa el espacio, el mas corto va rellenado con puntos guia y un
    cambio de indicacion de compas a mitad de pieza ocupa su propio segmento.
    """
    out = []
    for seg in content.split(" "):
        seg = _GUIDE_FILL.sub("", seg)
        if seg and not _TIME_ONLY.match(seg):
            out.append(seg)
    return out


def parse_reference(brf: str) -> List[Piece]:
    """Separa el BRF en piezas con sus compases por mano, en Braille ASCII.

    Cada paralela abre con la linea de mano derecha, que puede traer varios
    compases separados por espacios; la linea de mano izquierda trae los mismos
    compases en el mismo orden. Las lineas sangradas sin signo de mano
    continuan el ultimo compas de la ultima mano escrita.
    """
    pieces: List[Piece] = []
    current: Optional[Piece] = None
    group: List[Measure] = []
    side = "right"
    slot = 0
    for raw in brf.replace("\r", "").split("\n"):
        line = raw.rstrip()
        if not line.strip() or _PAGE_NUMBER.match(line):
            continue
        title = _TITLE.match(line)
        if title:
            current = Piece(index=len(pieces), title=title.group(1).rstrip("4"))
            pieces.append(current)
            group = []
            continue
        if current is None:
            continue
        hand = _HAND_LINE.match(line)
        if hand:
            number, sign, content = hand.groups()
            segments = _segments(content)
            if sign == ".":
                first = _number(number) if number else len(current.measures) + 1
                group = [Measure(number=first + k, right=seg) for k, seg in enumerate(segments)]
                current.measures += group
                side, slot = "right", len(group) - 1
            else:
                for k, seg in enumerate(segments[: len(group)]):
                    group[k].left += seg
                side, slot = "left", max(0, min(len(segments), len(group)) - 1)
            continue
        if not current.measures and _SIGNATURE.search(line):
            current.fifths, current.beats, current.beat_type = parse_signature(line)
            continue
        if group and raw.startswith("  "):
            segments = _segments(line.strip())
            for k, seg in enumerate(segments):
                if k > 0 and side == "right":
                    group.append(Measure(number=group[-1].number + 1, right=seg))
                    current.measures.append(group[-1])
                    slot = len(group) - 1
                    continue
                target = group[min(slot + k, len(group) - 1)]
                setattr(target, side, getattr(target, side) + seg)
            if side == "left":
                slot = min(slot + len(segments) - 1, len(group) - 1)
    return pieces


def expand_repeats(measures: List[Measure]) -> List[Measure]:
    """Orden en que suenan los compases si se tocan todas las repeticiones.

    Una seccion va desde el inicio o desde un signo de inicio de repeticion
    hasta el signo de fin. En la segunda vuelta se salta la casilla 1 y en la
    primera la casilla 2.
    """
    played: List[Measure] = []
    start = 0
    for i, m in enumerate(measures):
        if m.begins_repeat and i > start:
            played += measures[start:i]
            start = i
        if m.ends_repeat:
            section = measures[start:i + 1]
            played += [x for x in section if x.volta != 2]
            played += [x for x in section if x.volta != 1]
            start = i + 1
    return played + measures[start:]


def clean(content: str, removed: Counter) -> str:
    """Braille ASCII de un compas a Unicode sin los signos fuera del subset."""
    for token in _STRIPPED_TOKENS:
        if token in content:
            removed[token] += content.count(token)
            content = content.replace(token, "")
    cells = classify_cells(bt.brf_to_unicode(content))
    kept = []
    for symbol, category in cells:
        if category == UNKNOWN:
            removed[bt.unicode_to_brf(symbol)] += 1
        else:
            kept.append(symbol)
    return "".join(kept)


@dataclass
class HandStreams:
    right: str
    left: str
    measures_played: int
    removed: Dict[str, int]


def reference_streams(piece: Piece, repeats: bool = True) -> HandStreams:
    """Secuencias Braille por mano de una pieza, lista para compute_bsa."""
    measures = expand_repeats(piece.measures) if repeats else piece.measures
    removed: Counter = Counter()
    right = "".join(clean(m.right, removed) for m in measures)
    left = "".join(clean(m.left, removed) for m in measures)
    return HandStreams(right, left, len(measures), dict(removed))
