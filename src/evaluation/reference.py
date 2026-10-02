# Lectura de referencias Braille de piano en formato compas sobre compas para medir el BSA
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from braille_translator import braille_tables as bt

from .bsa import UNKNOWN, classify_cells

_HAND_LINE = re.compile(r"^\s*([a-j]*)'?\s*([._])>(.*)$")
_PAGE_NUMBER = re.compile(r'^\s*"?\d?#[a-j]+\s*$')
_TITLE = re.compile(r"^\s+(aria4|v>i,n #[a-j]+4)\s*$")
_KEY = r"(?:#[a-j][%<]|[%<*]*)"
_TIME = r"(?:#[a-j]+[0-9]+|[._]c)"
_SIGNATURE = re.compile(rf"(?:^|\s)({_KEY})({_TIME})\s*$")
_TIME_ONLY = re.compile(rf"^{_KEY}{_TIME}$")
_GUIDE_FILL = re.compile(r"'{2,}$")
# Encabezado de movimiento sin titulos de Goldberg: palabra con mayuscula tras una linea en blanco
_MOVEMENT = re.compile(r"^\s+,[a-z]")
_FINE = re.compile(r">fine\b")
_DA_CAPO = re.compile(r"d'c' al fine")
# Expresiones, matices y reguladores con signo de palabra; no son musica
_WORDS_MULTI = re.compile(r"(?<![<._])>[a-z][a-z'=!(7]*(?: +[a-z'=!(7]+)+>")
_WORDS_SINGLE = re.compile(r"(?<![<._])>(?:[a-z][a-z'=!]*|[34])")

_UPPER = {c: i for i, c in enumerate("jabcdefghi")}
_LOWER = {c: i for i, c in enumerate("0123456789")}

BEGIN_REPEAT = "<7"
END_REPEAT = "<2"
VOLTA = re.compile(r"#([12])")
# Pedal abajo y arriba; sin ellos se leerian como alteracion y ligadura
PEDAL_DOWN = "<c"
PEDAL_UP = "*c"

# Repeticiones y casillas ya usadas al expandir; el resto de signos ajenos al subset se quita al clasificar
_STRIPPED_TOKENS = (BEGIN_REPEAT, END_REPEAT, "<1", "#1", "#2", PEDAL_DOWN, PEDAL_UP)


@dataclass
class Measure:
    number: int
    right: str = ""
    left: str = ""
    fine: bool = False

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
    expressions: int = 0
    da_capo: bool = False

    @property
    def has_pickup(self) -> bool:
        return bool(self.measures) and self.measures[0].number == 0

    @property
    def quarters_per_measure(self) -> float:
        return self.beats * 4 / self.beat_type


def _number(letters: str) -> int:
    return int("".join(str(_UPPER[c]) for c in letters)) if letters else 0


def parse_signature(token: str) -> Tuple[int, int, int]:
    # Armadura y compas de encabezados como %#c4, *<<#b4, #f<#c4, %.c o %_c
    m = _SIGNATURE.search(token)
    if not m:
        raise ValueError(f"encabezado sin armadura ni compas: {token!r}")
    key, time = m.groups()
    if key.startswith("#"):
        fifths = _UPPER[key[1]] * (1 if key[2] == "%" else -1)
    else:
        fifths = key.count("%") - key.count("<")
    if time == ".c":
        return fifths, 4, 4
    if time == "_c":
        return fifths, 2, 2
    upper = re.match(r"#([a-j]+)", time).group(1)
    lower = time[1 + len(upper):]
    return fifths, _number(upper), int("".join(str(_LOWER[c]) for c in lower))


def _strip_words(content: str) -> Tuple[str, int]:
    # Cambia las palabras por relleno nulo del mismo largo para conservar las columnas
    count = 0
    for pattern in (_WORDS_MULTI, _WORDS_SINGLE):
        content, n = pattern.subn(lambda m: "\0" * len(m.group()), content)
        count += n
    return content, count


def _segments(content: str, offset: int = 0) -> List[Tuple[int, str]]:
    # Compases de una linea con su columna, sin puntos guia, palabras ni punto 3 inicial
    out = []
    for m in re.finditer(r"\S+", content):
        seg = _GUIDE_FILL.sub("", m.group().replace("\0", "")).lstrip("'")
        if seg and not _TIME_ONLY.match(seg):
            out.append((offset + m.start(), seg))
    return out


def parse_reference(brf: str) -> List[Piece]:
    # Piezas con sus compases por mano en Braille ASCII; sin titulos de Goldberg el archivo es una sola obra
    pieces: List[Piece] = []
    current: Optional[Piece] = None
    group: List[Measure] = []
    columns: List[int] = []
    side = "right"
    slot = 0
    after_blank = True
    for raw in brf.replace("\r", "").split("\n"):
        line = raw.rstrip()
        if line.strip() and _PAGE_NUMBER.match(line):
            continue
        blank_before, after_blank = after_blank, not line.strip()
        if not line.strip():
            continue
        title = _TITLE.match(line)
        if title:
            current = Piece(index=len(pieces), title=title.group(1).rstrip("4"))
            pieces.append(current)
            group = []
            continue
        hand = _HAND_LINE.match(line)
        if current is None and (hand or _SIGNATURE.search(line)):
            current = Piece(index=len(pieces), title="obra")
            pieces.append(current)
        if current is None:
            continue
        if not hand and current.measures and _MOVEMENT.match(line) and (blank_before or _SIGNATURE.search(line)):
            # Un encabezado sin compas en su linea conserva la armadura del movimiento anterior
            inherited = 0 if _SIGNATURE.search(line) else current.fifths
            current = Piece(index=len(pieces), title=line.split()[0].strip(",4"), fifths=inherited)
            pieces.append(current)
            group = []
        if hand:
            number, sign, content = hand.groups()
            current.da_capo |= bool(_DA_CAPO.search(content))
            marks_fine = bool(_FINE.search(content))
            content, words = _strip_words(content)
            current.expressions += words
            segments = _segments(content, hand.start(3))
            if sign == ".":
                # Una linea con solo palabras abre un compas que se llena en la continuacion
                segments = segments or [(hand.start(3), "")]
                first = _number(number) if number else len(current.measures) + 1
                group = [Measure(number=first + k, right=seg) for k, (_, seg) in enumerate(segments)]
                columns = [col for col, _ in segments]
                current.measures += group
                side, slot = "right", len(group) - 1
                if marks_fine:
                    group[-1].fine = True
            elif group:
                starts = {col for col, _ in segments}
                if all(c in starts for c in columns[1:]):
                    # Formato alineado; cada token va al compas de la derecha que empieza en su columna o antes
                    for col, seg in segments:
                        slot = max([k for k, c in enumerate(columns) if c <= col] or [0])
                        group[slot].left += seg
                else:
                    for k, (_, seg) in enumerate(segments[: len(group)]):
                        group[k].left += seg
                    slot = max(0, min(len(segments), len(group)) - 1)
                side = "left"
            continue
        if not current.measures and _SIGNATURE.search(line):
            fifths, current.beats, current.beat_type = parse_signature(line)
            if _SIGNATURE.search(line).group(1):
                current.fifths = fifths
            continue
        if group and raw.startswith("  "):
            content, words = _strip_words(line.strip())
            current.expressions += words
            segments = _segments(content)
            for k, (_, seg) in enumerate(segments):
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
    # Orden en que suenan los compases tocando las repeticiones; la casilla 1 solo en la primera vuelta
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
    # Braille ASCII de un compas a Unicode sin los signos fuera del subset
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
    played: List[Measure] = field(default_factory=list)


def reference_streams(piece: Piece, repeats: bool = True) -> HandStreams:
    # Secuencias Braille por mano de una pieza, listas para compute_bsa
    measures = expand_repeats(piece.measures) if repeats else list(piece.measures)
    if repeats and piece.da_capo:
        # Da capo al fine: vuelve al inicio sin repeticiones hasta el compas marcado con fine
        end = next((k for k, m in enumerate(piece.measures) if m.fine), len(piece.measures) - 1)
        measures += [m for m in piece.measures[:end + 1] if m.volta != 1]
    removed: Counter = Counter()
    right = "".join(clean(m.right, removed) for m in measures)
    left = "".join(clean(m.left, removed) for m in measures)
    return HandStreams(right, left, len(measures), dict(removed), measures)
