"""Pruebas del modulo AMT: contrato de eventos y cuantizador.

No requieren PyTorch: el wrapper del modelo se prueba con una salida simulada.
"""
import unittest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from amt.events import NoteEvent, PedalEvent, TranscriptionResult
from amt.quantizer import (
    largest_duration, midi_to_note, quantize, split_duration, ticks_per_measure,
)
from amt.transcriber import AMTTranscriber
from braille_translator.model import Chord, Note, Rest


def ev(onset, offset, pitch):
    return NoteEvent(onset_s=onset, offset_s=offset, midi_pitch=pitch)


class TestNoteEvent(unittest.TestCase):
    def test_offset_anterior_a_onset_es_invalido(self):
        with self.assertRaises(ValueError):
            NoteEvent(onset_s=1.0, offset_s=0.5, midi_pitch=60)

    def test_altura_fuera_de_rango_midi_es_invalida(self):
        with self.assertRaises(ValueError):
            NoteEvent(onset_s=0.0, offset_s=1.0, midi_pitch=200)

    def test_duracion(self):
        self.assertAlmostEqual(ev(0.5, 2.0, 60).duration_s, 1.5)


class TestSplitHands(unittest.TestCase):
    def test_do_central_va_a_mano_derecha(self):
        res = TranscriptionResult(notes=[ev(0, 1, 59), ev(0, 1, 60)])
        right, left = res.split_hands()
        self.assertEqual([n.midi_pitch for n in right], [60])
        self.assertEqual([n.midi_pitch for n in left], [59])

    def test_umbral_configurable(self):
        res = TranscriptionResult(notes=[ev(0, 1, 60), ev(0, 1, 70)])
        right, _ = res.split_hands(split_pitch=65)
        self.assertEqual([n.midi_pitch for n in right], [70])


class TestPitchMapping(unittest.TestCase):
    def test_do_central_es_octava_4(self):
        self.assertEqual(midi_to_note(60), ("C", 0, 4))

    def test_alteracion_se_conserva(self):
        self.assertEqual(midi_to_note(61), ("C", 1, 4))

    def test_la_440_es_la_octava_4(self):
        self.assertEqual(midi_to_note(69), ("A", 0, 4))


class TestDurations(unittest.TestCase):
    def test_simbolo_mayor_que_cabe(self):
        self.assertEqual(largest_duration(16), ("whole", 0))
        self.assertEqual(largest_duration(6), ("quarter", 1))

    def test_duracion_no_representable_se_recorta(self):
        self.assertEqual(largest_duration(5), ("quarter", 0))

    def test_silencio_se_parte_en_varios(self):
        self.assertEqual(split_duration(5), [("quarter", 0), ("16th", 0)])

    def test_ticks_por_compas(self):
        self.assertEqual(ticks_per_measure(4, 4), 16)
        self.assertEqual(ticks_per_measure(3, 4), 12)
        self.assertEqual(ticks_per_measure(6, 8), 12)


class TestQuantize(unittest.TestCase):
    """Tempo 60 bpm => negra = 1 s, semicorchea = 0.25 s."""

    def test_cuatro_negras_dan_un_compas(self):
        res = TranscriptionResult(notes=[ev(i, i + 1, 60 + i) for i in range(4)])
        score = quantize(res, tempo_bpm=60)
        self.assertEqual(len(score.right.measures), 1)
        eventos = score.right.measures[0].events
        self.assertEqual(len(eventos), 4)
        self.assertTrue(all(e.duration_type == "quarter" for e in eventos))

    def test_notas_simultaneas_forman_acorde(self):
        res = TranscriptionResult(notes=[ev(0, 1, 60), ev(0, 1, 64), ev(0, 1, 67)])
        score = quantize(res, tempo_bpm=60)
        primero = score.right.measures[0].events[0]
        self.assertIsInstance(primero, Chord)
        self.assertEqual(len(primero.notes), 3)

    def test_silencio_inicial_se_rellena(self):
        res = TranscriptionResult(notes=[ev(2.0, 3.0, 60)])
        score = quantize(res, tempo_bpm=60)
        self.assertIsInstance(score.right.measures[0].events[0], Rest)

    def test_manos_tienen_igual_numero_de_compases(self):
        res = TranscriptionResult(notes=[ev(0, 4, 72), ev(0, 1, 48)])
        score = quantize(res, tempo_bpm=60)
        self.assertEqual(len(score.right.measures), len(score.left.measures))

    def test_mano_vacia_se_rellena_con_silencios(self):
        res = TranscriptionResult(notes=[ev(0, 1, 72)])
        score = quantize(res, tempo_bpm=60)
        self.assertTrue(all(
            isinstance(e, Rest) for m in score.left.measures for e in m.events
        ))

    def test_nota_no_cruza_la_barra_de_compas(self):
        res = TranscriptionResult(notes=[ev(3.0, 7.0, 60)])   # cruza el compas 1
        score = quantize(res, tempo_bpm=60)
        primer_compas = score.right.measures[0].events
        notas = [e for e in primer_compas if isinstance(e, Note)]
        self.assertEqual(len(notas), 1)
        self.assertEqual(notas[0].duration_type, "quarter")

    def test_alteracion_llega_al_ast(self):
        res = TranscriptionResult(notes=[ev(0, 1, 61)])
        score = quantize(res, tempo_bpm=60)
        nota = score.right.measures[0].events[0]
        self.assertEqual((nota.step, nota.alter), ("C", 1))

    def test_tempo_invalido(self):
        with self.assertRaises(ValueError):
            quantize(TranscriptionResult(), tempo_bpm=0)

    def test_tempo_doble_reduce_las_figuras(self):
        res = TranscriptionResult(notes=[ev(0, 1, 60)])
        lento = quantize(res, tempo_bpm=60).right.measures[0].events[0]
        rapido = quantize(res, tempo_bpm=120).right.measures[0].events[0]
        self.assertEqual(lento.duration_type, "quarter")
        self.assertEqual(rapido.duration_type, "half")


class TestTranscriberContract(unittest.TestCase):
    def test_salida_del_modelo_se_convierte_a_eventos(self):
        crudo = {
            "est_note_events": [
                {"onset_time": 0.0, "offset_time": 0.5, "midi_note": 60, "velocity": 90},
            ],
            "est_pedal_events": [{"onset_time": 0.0, "offset_time": 1.0}],
        }
        res = AMTTranscriber.from_model_output(crudo, source="x.wav", duration_s=1.0)
        self.assertEqual(len(res.notes), 1)
        self.assertEqual(res.notes[0].midi_pitch, 60)
        self.assertEqual(len(res.pedals), 1)
        self.assertIsInstance(res.pedals[0], PedalEvent)

    def test_importar_el_wrapper_no_arrastra_torch(self):
        import amt.transcriber   # noqa: F401
        self.assertNotIn("torch", sys.modules)

    def test_transcribir_sin_el_modelo_da_error_accionable(self):
        if AMTTranscriber.available():
            self.skipTest("el modelo esta instalado")
        with self.assertRaises(ImportError) as ctx:
            AMTTranscriber()._load()
        self.assertIn("requirements.txt", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
