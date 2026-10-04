# BSA del pipeline completo contra una referencia Braille humana, alineando cada mano completa
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable, Dict, List, Optional, Tuple

from amt.beats import beat_unit_quarters, follow_tempo
from amt.events import NoteEvent, TranscriptionResult
from amt.quantizer import quantize
from braille_translator.translator import translate_score

from .bsa import BsaResult, CategoryScore, classify_cells, compute_bsa
from .reference import HandStreams, Piece, reference_streams

MAX_CELLS = 40_000_000


def merge(a: BsaResult, b: BsaResult) -> BsaResult:
    # Suma dos resultados, por ejemplo las dos manos de una pieza
    out = BsaResult(
        total_ref=a.total_ref + b.total_ref, total_hyp=a.total_hyp + b.total_hyp,
        matches=a.matches + b.matches, substitutions=a.substitutions + b.substitutions,
        deletions=a.deletions + b.deletions, insertions=a.insertions + b.insertions,
    )
    for part in (a, b):
        for cat, s in part.per_category.items():
            acc = out.per_category.setdefault(cat, CategoryScore())
            acc.ref += s.ref
            acc.hyp += s.hyp
            acc.matches += s.matches
            acc.substitutions += s.substitutions
            acc.deletions += s.deletions
            acc.insertions += s.insertions
    return out


def note_count(streams: HandStreams) -> int:
    # Notas que suenan segun la referencia; cada nota o intervalo cuenta una
    cells = classify_cells(streams.right + streams.left)
    return sum(1 for _, cat in cells if cat in ("notas", "intervalos"))


def shifted_result(notes: List[List[float]], duration_s: float) -> TranscriptionResult:
    # Desplaza las notas para que el primer ataque caiga en cero
    start = min(n[0] for n in notes)
    events = [
        NoteEvent(onset_s=n[0] - start, offset_s=max(n[1], n[0] + 1e-3) - start,
                  midi_pitch=int(n[2]), velocity=int(n[3]) if len(n) > 3 else 80)
        for n in notes
    ]
    return TranscriptionResult(notes=events, duration_s=duration_s - start)


def estimate_tempo(result: TranscriptionResult, piece: Piece, measures_played: int,
                   pickup_quarters: float = 0.0) -> float:
    # Negras por minuto suponiendo que el ultimo ataque cae en el primer tiempo del ultimo compas
    span = max(n.onset_s for n in result.notes)
    full = measures_played - 1 - (1 if pickup_quarters else 0)
    quarters = full * piece.quarters_per_measure + pickup_quarters
    return 60.0 * quarters / span


def place_pickup(result: TranscriptionResult, piece: Piece, tempo_bpm: float,
                 pickup_quarters: float) -> TranscriptionResult:
    # Retrasa las notas para que la anacrusa ocupe el final de su compas
    if not pickup_quarters:
        return result
    delay = (piece.quarters_per_measure - pickup_quarters) * 60.0 / tempo_bpm
    notes = [NoteEvent(n.onset_s + delay, n.offset_s + delay, n.midi_pitch, n.velocity) for n in result.notes]
    return TranscriptionResult(notes=notes, duration_s=result.duration_s + delay)


@dataclass
class PieceEvaluation:
    piece: int
    repeats: bool
    tempo_bpm: float
    notes_transcribed: int
    notes_reference: int
    removed_reference_cells: int
    right: BsaResult
    left: BsaResult
    both: BsaResult
    pitch_agreement: float = 0.0
    # Compases generados por mano y la referencia tocada, para el desglose en alturas, ritmo y fraseo
    hyp_measures: Tuple[List[str], List[str]] = ((), ())
    reference: Optional[HandStreams] = None

    def row(self) -> Dict[str, float]:
        return {
            "pieza": self.piece,
            "repeticiones": self.repeats,
            "tempo_bpm": round(self.tempo_bpm, 1),
            "notas_transcritas": self.notes_transcribed,
            "notas_referencia": self.notes_reference,
            "celdas_quitadas_referencia": self.removed_reference_cells,
            "bsa": self.both.bsa,
            "bsa_ponderado": self.both.weighted_bsa,
            "bsa_md": self.right.bsa,
            "bsa_mi": self.left.bsa,
            "coincidencia_alturas": self.pitch_agreement,
            "celdas_ref": self.both.total_ref,
            "celdas_gen": self.both.total_hyp,
            "aciertos": self.both.matches,
            "sustituciones": self.both.substitutions,
            "omisiones": self.both.deletions,
            "inserciones": self.both.insertions,
        }


def evaluate_piece(piece: Piece, notes: List[List[float]], duration_s: float,
                   repeats: Optional[bool] = None, legato: float = 0.0,
                   pre: Optional[Callable[[TranscriptionResult], TranscriptionResult]] = None,
                   hands: Optional[Callable] = None, voices: tuple = (),
                   pickup_quarters: float = 0.0, track: bool = False,
                   grouping: bool = False, drop_penalty: Optional[float] = None,
                   voice_threshold: float = 0.0, slur_ratio: Optional[float] = None) -> PieceEvaluation:
    # pre limpia las notas, hands reparte las manos y track sigue el pulso en vez de usar un tempo fijo
    result = shifted_result(notes, duration_s)
    if pre is not None:
        result = pre(result)
    with_rep, without_rep = reference_streams(piece, True), reference_streams(piece, False)
    if repeats is None:
        # Las dos hipotesis difieren casi al doble, por eso la frontera es la media geometrica
        frontera = (note_count(with_rep) * note_count(without_rep)) ** 0.5
        repeats = len(result.notes) >= frontera
    ref = with_rep if repeats else without_rep

    tempo = estimate_tempo(result, piece, ref.measures_played, pickup_quarters)
    if track:
        unit = beat_unit_quarters(piece.beat_type)
        per_bar = int(round(piece.quarters_per_measure / unit))
        start = int(round((piece.quarters_per_measure - pickup_quarters) / unit)) % per_bar if pickup_quarters else 0
        result = follow_tempo(result, tempo, piece.beat_type, beats_per_bar=per_bar,
                              drop_penalty=drop_penalty, start_position=start)
        tempo = 60.0
    result = place_pickup(result, piece, tempo, pickup_quarters)
    score = quantize(result, tempo_bpm=tempo, beats=piece.beats,
                     beat_type=piece.beat_type, fifths=piece.fifths, legato=legato,
                     hands=hands(result.notes) if hands is not None else None,
                     voices=voices, voice_threshold=voice_threshold, slur_ratio=slur_ratio)
    right, left = translate_score(score, measures_per_line=1, grouping=grouping)
    hyp_right, hyp_left = "".join(right), "".join(left)

    alturas = pitch_agreement(ref.right + ref.left, hyp_right + hyp_left)
    right_bsa = compute_bsa(ref.right, hyp_right, MAX_CELLS)
    left_bsa = compute_bsa(ref.left, hyp_left, MAX_CELLS)
    return PieceEvaluation(
        piece=piece.index,
        repeats=repeats,
        tempo_bpm=tempo,
        notes_transcribed=len(result.notes),
        notes_reference=note_count(ref),
        removed_reference_cells=sum(ref.removed.values()),
        right=right_bsa,
        left=left_bsa,
        both=merge(right_bsa, left_bsa),
        pitch_agreement=alturas,
        hyp_measures=(right, left),
        reference=ref,
    )


def _step(cell: str) -> str:
    # Nota sin su valor, quitando los puntos 3 y 6
    return chr(0x2800 + ((ord(cell) - 0x2800) & ~0x24))


def pitch_agreement(reference: str, hypothesis: str) -> float:
    # Coincidencia de alturas ignorando la duracion, para separar el error de altura del ritmico
    ref = [_step(c) for c, cat in classify_cells(reference) if cat == "notas"]
    hyp = [_step(c) for c, cat in classify_cells(hypothesis) if cat == "notas"]
    if not ref and not hyp:
        return 1.0
    return SequenceMatcher(None, ref, hyp, autojunk=False).ratio()
