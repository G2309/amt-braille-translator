"""Pruebas de la medicion de latencia del pipeline."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from amt.events import TranscriptionResult
from evaluation.latency import (
    LATENCY_THRESHOLD, MIN_RUNS_WITHIN, LatencyRun, LatencySummary, StageTimings,
    measure_end_to_end, synthetic_result, time_deterministic,
)


def run_con_ratio(ratio: float, duracion: float = 100.0) -> LatencyRun:
    return LatencyRun(source="x", audio_duration_s=duracion,
                      timings=StageTimings(amt_s=ratio * duracion))


class TestSyntheticResult(unittest.TestCase):
    def test_densidad_y_duracion(self):
        r = synthetic_result(60, notes_per_second=10)
        self.assertEqual(len(r.notes), 600)
        self.assertEqual(r.duration_s, 60)

    def test_ninguna_nota_se_sale_del_audio(self):
        r = synthetic_result(30, notes_per_second=20)
        self.assertTrue(all(n.offset_s <= 30 for n in r.notes))

    def test_es_reproducible_con_la_misma_semilla(self):
        a = synthetic_result(10, seed=1)
        b = synthetic_result(10, seed=1)
        self.assertEqual([n.midi_pitch for n in a.notes], [n.midi_pitch for n in b.notes])


class TestStageTimings(unittest.TestCase):
    def test_el_total_suma_todas_las_etapas(self):
        t = StageTimings(amt_s=1.0, quantize_s=0.1, translate_s=0.2,
                         render_s=0.3, export_s=0.4)
        self.assertAlmostEqual(t.deterministic_s, 1.0)
        self.assertAlmostEqual(t.total_s, 2.0)


class TestTimeDeterministic(unittest.TestCase):
    def test_mide_todas_las_etapas(self):
        t = time_deterministic(synthetic_result(10))
        for etapa in (t.quantize_s, t.translate_s, t.render_s):
            self.assertGreater(etapa, 0)
        self.assertEqual(t.amt_s, 0.0)

    def test_sin_ruta_de_salida_no_cronometra_exportacion(self):
        self.assertEqual(time_deterministic(synthetic_result(5)).export_s, 0.0)

    def test_con_ruta_de_salida_escribe_el_archivo(self):
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".brf", delete=False)
        f.close()
        self.addCleanup(os.unlink, f.name)
        t = time_deterministic(synthetic_result(5), output_path=f.name)
        self.assertGreater(t.export_s, 0)
        self.assertGreater(os.path.getsize(f.name), 0)


class TestMeasureEndToEnd(unittest.TestCase):
    def test_incluye_la_etapa_acustica_y_la_determinista(self):
        def transcribir(_path):
            return synthetic_result(20)

        run = measure_end_to_end("a.wav", transcribir)
        self.assertEqual(run.audio_duration_s, 20)
        self.assertEqual(run.n_notes, 200)
        self.assertGreater(run.timings.amt_s, 0)
        self.assertGreater(run.timings.deterministic_s, 0)

    def test_el_cociente_usa_la_duracion_del_audio(self):
        run = run_con_ratio(0.5)
        self.assertAlmostEqual(run.ratio, 0.5)
        self.assertTrue(run.within_threshold)

    def test_audio_de_duracion_cero_no_divide_entre_cero(self):
        run = LatencyRun(source="x", audio_duration_s=0.0, timings=StageTimings(amt_s=1.0))
        self.assertEqual(run.ratio, 0.0)

    def test_serializa_a_diccionario_plano(self):
        d = run_con_ratio(0.3).as_dict()
        for clave in ("source", "audio_duration_s", "ratio", "within_threshold",
                      "amt_s", "deterministic_s", "total_s"):
            self.assertIn(clave, d)


class TestLatencySummary(unittest.TestCase):
    def test_el_umbral_es_inclusivo(self):
        self.assertTrue(run_con_ratio(LATENCY_THRESHOLD).within_threshold)
        self.assertFalse(run_con_ratio(LATENCY_THRESHOLD + 0.01).within_threshold)

    def test_exactamente_el_noventa_por_ciento_cumple(self):
        runs = [run_con_ratio(0.5) for _ in range(9)] + [run_con_ratio(3.0)]
        s = LatencySummary(runs)
        self.assertAlmostEqual(s.proportion_within, MIN_RUNS_WITHIN)
        self.assertTrue(s.meets_criterion)

    def test_por_debajo_del_noventa_no_cumple(self):
        runs = [run_con_ratio(0.5) for _ in range(8)] + [run_con_ratio(3.0)] * 2
        self.assertFalse(LatencySummary(runs).meets_criterion)

    def test_sin_ejecuciones_no_cumple(self):
        self.assertFalse(LatencySummary([]).meets_criterion)

    def test_percentiles(self):
        s = LatencySummary([run_con_ratio(r) for r in (0.1, 0.2, 0.3, 0.4, 0.5)])
        self.assertAlmostEqual(s.percentile(0.5), 0.3)
        self.assertAlmostEqual(s.percentile(1.0), 0.5)

    def test_el_reparto_por_etapa_suma_uno(self):
        runs = [LatencyRun("x", 10.0, StageTimings(amt_s=1.0, quantize_s=0.5,
                                                   translate_s=0.3, render_s=0.1,
                                                   export_s=0.1))]
        share = LatencySummary(runs).stage_share()
        self.assertAlmostEqual(sum(share.values()), 1.0)
        self.assertAlmostEqual(share["amt"], 0.5)

    def test_el_reporte_dice_si_cumple(self):
        s = LatencySummary([run_con_ratio(0.1) for _ in range(10)])
        self.assertIn("CUMPLE", s.report())


class TestLatenciaDeterministaEsDespreciable(unittest.TestCase):
    """La etapa determinista no debe pesar en el criterio de latencia."""

    def test_cinco_minutos_se_traducen_muy_por_debajo_del_umbral(self):
        t = time_deterministic(synthetic_result(300, notes_per_second=10))
        self.assertLess(t.deterministic_s / 300, 0.01)


if __name__ == "__main__":
    unittest.main()
