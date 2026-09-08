"""Medicion de latencia del pipeline.

El cuarto objetivo especifico exige que el proceso completo termine en un
tiempo menor o igual a 1.5 veces la duracion del audio, en al menos el 90 %
de las ejecuciones. Este modulo cronometra cada etapa por separado para saber
no solo si se cumple, sino donde se va el tiempo.

La etapa acustica necesita GPU y modelo; la determinista no depende de nada
externo y puede medirse en cualquier maquina con `synthetic_result`.
"""
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional

from amt.events import NoteEvent, TranscriptionResult
from amt.quantizer import quantize
from braille_translator import braille_tables as bt
from braille_translator.brf_exporter import export_brf
from braille_translator.renderer import DEFAULT_MEASURES_PER_LINE, render_bar_over_bar
from braille_translator.translator import translate_score

LATENCY_THRESHOLD = 1.5     # veces la duracion del audio
MIN_RUNS_WITHIN = 0.90      # proporcion de ejecuciones que deben cumplirlo


@dataclass
class StageTimings:
    """Segundos por etapa de una sola ejecucion."""
    amt_s: float = 0.0
    quantize_s: float = 0.0
    translate_s: float = 0.0
    render_s: float = 0.0
    export_s: float = 0.0

    @property
    def deterministic_s(self) -> float:
        return self.quantize_s + self.translate_s + self.render_s + self.export_s

    @property
    def total_s(self) -> float:
        return self.amt_s + self.deterministic_s


@dataclass
class LatencyRun:
    source: str
    audio_duration_s: float
    timings: StageTimings
    n_notes: int = 0

    @property
    def ratio(self) -> float:
        return self.timings.total_s / self.audio_duration_s if self.audio_duration_s else 0.0

    @property
    def within_threshold(self) -> bool:
        return self.ratio <= LATENCY_THRESHOLD

    def as_dict(self) -> dict:
        d = {"source": self.source, "audio_duration_s": self.audio_duration_s,
             "n_notes": self.n_notes, "ratio": self.ratio,
             "within_threshold": self.within_threshold}
        d.update(asdict(self.timings))
        d["deterministic_s"] = self.timings.deterministic_s
        d["total_s"] = self.timings.total_s
        return d


def synthetic_result(duration_s: float, notes_per_second: float = 10.0,
                     seed: int = 22779) -> TranscriptionResult:
    """Salida acustica simulada, para medir la etapa determinista sin modelo.

    La densidad por omision, diez notas por segundo, esta en el rango del
    repertorio pianistico de concierto de MAESTRO.
    """
    rng = random.Random(seed)
    notas: List[NoteEvent] = []
    n = int(duration_s * notes_per_second)
    for _ in range(n):
        onset = rng.uniform(0, duration_s)
        largo = rng.uniform(0.1, 1.5)
        notas.append(NoteEvent(
            onset_s=onset,
            offset_s=min(onset + largo, duration_s),
            midi_pitch=rng.randint(21, 108),
            velocity=rng.randint(40, 110),
        ))
    notas.sort(key=lambda x: x.onset_s)
    return TranscriptionResult(notes=notas, duration_s=duration_s,
                               source=f"sintetico-{duration_s:.0f}s")


def time_deterministic(result: TranscriptionResult, output_path: Optional[str] = None,
                       tempo_bpm: float = 60.0, beats: int = 4, beat_type: int = 4,
                       fifths: int = 0,
                       measures_per_line: int = DEFAULT_MEASURES_PER_LINE) -> StageTimings:
    """Cronometra cuantizacion, traduccion, renderizado y exportacion."""
    t = StageTimings()

    t0 = time.perf_counter()
    score = quantize(result, tempo_bpm=tempo_bpm, beats=beats,
                     beat_type=beat_type, fifths=fifths)
    t.quantize_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    rh, lh = translate_score(score, measures_per_line)
    t.translate_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    header = bt.key_signature(score.fifths) + bt.time_signature(score.beats, score.beat_type)
    braille = render_bar_over_bar(rh, lh, measures_per_line, header=header)
    t.render_s = time.perf_counter() - t0

    if output_path:
        t0 = time.perf_counter()
        export_brf(braille, output_path)
        t.export_s = time.perf_counter() - t0
    return t


def measure_end_to_end(audio_path: str, transcribe: Callable[[str], TranscriptionResult],
                       output_path: Optional[str] = None, **params) -> LatencyRun:
    """Mide el pipeline completo sobre un archivo de audio.

    `transcribe` se recibe como argumento para no importar PyTorch aqui y
    poder inyectar un transcriptor simulado en las pruebas.
    """
    t0 = time.perf_counter()
    result = transcribe(audio_path)
    amt_s = time.perf_counter() - t0

    timings = time_deterministic(result, output_path=output_path, **params)
    timings.amt_s = amt_s
    return LatencyRun(source=audio_path, audio_duration_s=result.duration_s,
                      timings=timings, n_notes=len(result.notes))


@dataclass
class LatencySummary:
    runs: List[LatencyRun] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.runs)

    @property
    def ratios(self) -> List[float]:
        return sorted(r.ratio for r in self.runs)

    @property
    def proportion_within(self) -> float:
        if not self.runs:
            return 0.0
        return sum(r.within_threshold for r in self.runs) / len(self.runs)

    @property
    def meets_criterion(self) -> bool:
        return self.proportion_within >= MIN_RUNS_WITHIN

    def percentile(self, p: float) -> float:
        vals = self.ratios
        if not vals:
            return 0.0
        pos = min(int(round(p * (len(vals) - 1))), len(vals) - 1)
        return vals[pos]

    def stage_share(self) -> Dict[str, float]:
        """Proporcion del tiempo total que consume cada etapa."""
        total = sum(r.timings.total_s for r in self.runs)
        if not total:
            return {}
        acum = {"amt": 0.0, "quantize": 0.0, "translate": 0.0, "render": 0.0, "export": 0.0}
        for r in self.runs:
            acum["amt"] += r.timings.amt_s
            acum["quantize"] += r.timings.quantize_s
            acum["translate"] += r.timings.translate_s
            acum["render"] += r.timings.render_s
            acum["export"] += r.timings.export_s
        return {k: v / total for k, v in acum.items()}

    def report(self) -> str:
        veredicto = "CUMPLE" if self.meets_criterion else "NO cumple"
        filas = [
            f"Ejecuciones            : {self.n}",
            f"Dentro de {LATENCY_THRESHOLD}x         : {self.proportion_within:.1%} "
            f"(exigido {MIN_RUNS_WITHIN:.0%}) -> {veredicto}",
            f"Cociente mediano       : {self.percentile(0.5):.4f}",
            f"Cociente p90           : {self.percentile(0.9):.4f}",
            f"Cociente maximo        : {self.percentile(1.0):.4f}",
        ]
        share = self.stage_share()
        if share:
            filas.append("")
            filas.append("Reparto del tiempo total por etapa")
            for etapa, frac in share.items():
                filas.append(f"  {etapa:<10}{frac:>8.2%}")
        return "\n".join(filas)
