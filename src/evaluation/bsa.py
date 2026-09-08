"""Exactitud de Simbolo Braille (BSA).

Compara un archivo BRF generado contra uno de referencia celda a celda y
desglosa las diferencias por categoria sintactica.

El calculo tiene tres pasos: clasificar cada celda de ambos textos en una de
las nueve categorias del subset, alinear las dos secuencias con distancia de
edicion, y contar aciertos, sustituciones, omisiones e inserciones por
categoria. El procedimiento completo esta en docs/bsa_metric.md.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from braille_translator import braille_tables as bt

# Pesos por categoria (docs/braille_rules_subset.md, seccion 10)
CATEGORY_WEIGHTS: Dict[str, float] = {
    "notas": 0.25,
    "octavas": 0.20,
    "alteraciones": 0.15,
    "intervalos": 0.10,
    "in_accords": 0.10,
    "ligaduras": 0.05,
    "barras": 0.05,
    "bar_over_bar": 0.05,
    "manos": 0.05,
}

UNKNOWN = "desconocido"

# Simbolos de mas de una celda, del mas largo al mas corto: el primero que
# encaje gana, para que ⠣⠅⠄ no se lea como ⠣⠅ seguido de un puntillo.
_MULTI: List[Tuple[str, str]] = sorted(
    [
        (bt.DOUBLE_BAR, "barras"),
        (bt.FINAL_BAR, "barras"),
        (bt.RIGHT_HAND, "manos"),
        (bt.LEFT_HAND, "manos"),
        (bt.IN_ACCORD, "in_accords"),
        (bt.PARTIAL_IN_ACCORD, "in_accords"),
        (bt.MEASURE_DIVISION, "in_accords"),
        (bt.TIE, "ligaduras"),
        (bt.CHORD_TIE, "ligaduras"),
        (bt.SLUR_OPEN, "ligaduras"),
        (bt.SLUR_CLOSE, "ligaduras"),
    ],
    key=lambda pair: -len(pair[0]),
)

_OCTAVES = set(bt.OCTAVE_SIGN.values())
_ACCIDENTALS = {bt.ACCIDENTAL[1], bt.ACCIDENTAL[-1], bt.ACCIDENTAL[0]}
_INTERVALS = set(bt.INTERVAL.values())
_RESTS = set(bt.REST.values())
_NOTES = {
    bt.note_cell(step, dtype)
    for step in bt.NOTE_BASE
    for dtype in bt.DURATION_EXTRA_DOTS
}
_DIGITS = set(bt.UPPER_DIGIT.values()) | set(bt.LOWER_DIGIT.values())
_EMPTY = "⠀"


def classify_cells(text: str) -> List[Tuple[str, str]]:
    """Braille Unicode -> [(celda, categoria)], una entrada por celda.

    Los simbolos de varias celdas se reconocen enteros pero se devuelven
    celda a celda, cada una con la categoria del simbolo al que pertenece:
    asi el conteo sigue siendo por celdas y la categoria es la correcta.
    """
    out: List[Tuple[str, str]] = []
    prev = ""            # categoria de la celda anterior
    in_number = False    # dentro de una cifra (armadura o compas)
    i = 0
    while i < len(text):
        ch = text[i]

        if ch in ("\n", "\r", "\f"):
            # el salto de linea es estructura de la paralela
            if ch != "\r":
                out.append((ch, "bar_over_bar"))
                prev, in_number = "bar_over_bar", False
            i += 1
            continue

        matched = False
        for symbol, category in _MULTI:
            if text.startswith(symbol, i):
                out.extend((c, category) for c in symbol)
                prev, in_number = category, False
                i += len(symbol)
                matched = True
                break
        if matched:
            continue

        if ch in (_EMPTY, " "):
            category = "barras"
            in_number = False
        elif ch == bt.NUMBER_SIGN:
            # misma celda que el intervalo de 4a: manda el contexto
            if prev in ("notas", "intervalos"):
                category = "intervalos"
            else:
                category = "alteraciones"
                in_number = True
        elif in_number and ch in _DIGITS:
            category = "alteraciones"
        elif ch in _OCTAVES:
            category = "octavas"
        elif ch in _ACCIDENTALS:
            category = "alteraciones"
        elif ch == bt.SLUR:
            category = "ligaduras"
        elif ch in _NOTES or ch in _RESTS:
            category = "notas"
            in_number = False
        elif ch in _INTERVALS:
            category = "intervalos"
        elif ch == bt.DOT:
            # puntillo tras nota o intervalo; si no, linea guia del relleno
            category = "notas" if prev in ("notas", "intervalos") else "bar_over_bar"
        else:
            category = UNKNOWN

        out.append((ch, category))
        prev = category
        i += 1
    return out


def load_braille(path: str) -> str:
    """Lee un archivo BRF o Braille Unicode y devuelve siempre Unicode."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if any("⠀" <= c <= "⣿" for c in content):
        return content
    return bt.brf_to_unicode(content)


@dataclass
class CategoryScore:
    ref: int = 0
    hyp: int = 0
    matches: int = 0
    substitutions: int = 0
    deletions: int = 0
    insertions: int = 0

    @property
    def bsa(self) -> float:
        base = max(self.ref, self.hyp)
        return self.matches / base if base else 1.0


@dataclass
class BsaResult:
    total_ref: int = 0
    total_hyp: int = 0
    matches: int = 0
    substitutions: int = 0
    deletions: int = 0
    insertions: int = 0
    per_category: Dict[str, CategoryScore] = field(default_factory=dict)

    @property
    def bsa(self) -> float:
        """Celdas coincidentes sobre la secuencia mas larga."""
        base = max(self.total_ref, self.total_hyp)
        return self.matches / base if base else 1.0

    @property
    def weighted_bsa(self) -> float:
        """BSA ponderado con los pesos del subset.

        Solo entran las categorias presentes en la referencia y los pesos se
        renormalizan, para que un fragmento sin in-accords no quede penalizado
        por una categoria que no aparece.
        """
        activos = {
            cat: CATEGORY_WEIGHTS[cat]
            for cat, score in self.per_category.items()
            if cat in CATEGORY_WEIGHTS and score.ref > 0
        }
        total = sum(activos.values())
        if not total:
            return self.bsa
        return sum(w * self.per_category[cat].bsa for cat, w in activos.items()) / total

    def report(self) -> str:
        filas = [
            f"BSA global      : {self.bsa:.2%}",
            f"BSA ponderado   : {self.weighted_bsa:.2%}",
            f"celdas ref/gen  : {self.total_ref} / {self.total_hyp}",
            f"aciertos        : {self.matches}",
            f"sustituciones   : {self.substitutions}",
            f"omisiones       : {self.deletions}",
            f"inserciones     : {self.insertions}",
            "",
            f"{'categoria':<14}{'ref':>6}{'gen':>6}{'ok':>6}{'sust':>6}{'omi':>6}{'ins':>6}{'BSA':>9}",
        ]
        orden = list(CATEGORY_WEIGHTS) + [UNKNOWN]
        for cat in orden:
            s = self.per_category.get(cat)
            if s is None or (s.ref == 0 and s.hyp == 0):
                continue
            filas.append(
                f"{cat:<14}{s.ref:>6}{s.hyp:>6}{s.matches:>6}"
                f"{s.substitutions:>6}{s.deletions:>6}{s.insertions:>6}{s.bsa:>9.2%}"
            )
        return "\n".join(filas)


def _align(ref: List[str], hyp: List[str]) -> List[Tuple[str, int, int]]:
    """Alineamiento optimo por distancia de edicion (Wagner-Fischer).

    Devuelve operaciones (match | sub | del | ins) con los indices que
    consumen en cada secuencia.
    """
    n, m = len(ref), len(hyp)
    dist = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dist[i][0] = i
    for j in range(1, m + 1):
        dist[0][j] = j
    for i in range(1, n + 1):
        ref_i = ref[i - 1]
        fila, previa = dist[i], dist[i - 1]
        for j in range(1, m + 1):
            coste = 0 if ref_i == hyp[j - 1] else 1
            fila[j] = min(previa[j - 1] + coste, previa[j] + 1, fila[j - 1] + 1)

    ops: List[Tuple[str, int, int]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            coste = 0 if ref[i - 1] == hyp[j - 1] else 1
            if dist[i][j] == dist[i - 1][j - 1] + coste:
                ops.append(("match" if coste == 0 else "sub", i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and dist[i][j] == dist[i - 1][j] + 1:
            ops.append(("del", i - 1, -1))
            i -= 1
            continue
        ops.append(("ins", -1, j - 1))
        j -= 1
    ops.reverse()
    return ops


def compute_bsa(reference: str, hypothesis: str, max_cells: int = 4_000_000) -> BsaResult:
    """Compara dos textos Braille Unicode y devuelve el desglose del BSA."""
    ref_cells = classify_cells(reference)
    hyp_cells = classify_cells(hypothesis)

    if len(ref_cells) * len(hyp_cells) > max_cells:
        raise ValueError(
            f"comparacion de {len(ref_cells)}x{len(hyp_cells)} celdas supera el limite; "
            "comparar por paralelas o subir max_cells"
        )

    result = BsaResult(total_ref=len(ref_cells), total_hyp=len(hyp_cells))

    def score(cat: str) -> CategoryScore:
        return result.per_category.setdefault(cat, CategoryScore())

    for cat in {c for _, c in ref_cells}:
        score(cat).ref = sum(1 for _, c in ref_cells if c == cat)
    for cat in {c for _, c in hyp_cells}:
        score(cat).hyp = sum(1 for _, c in hyp_cells if c == cat)

    for op, i, j in _align([c for c, _ in ref_cells], [c for c, _ in hyp_cells]):
        if op == "match":
            result.matches += 1
            score(ref_cells[i][1]).matches += 1
        elif op == "sub":
            result.substitutions += 1
            score(ref_cells[i][1]).substitutions += 1
        elif op == "del":
            result.deletions += 1
            score(ref_cells[i][1]).deletions += 1
        else:
            result.insertions += 1
            score(hyp_cells[j][1]).insertions += 1
    return result


def compare_files(reference_path: str, hypothesis_path: str) -> BsaResult:
    return compute_bsa(load_braille(reference_path), load_braille(hypothesis_path))
