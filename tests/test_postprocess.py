import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from amt.events import NoteEvent, TranscriptionResult
from amt.postprocess import collapse_trills, drop_octave_ghosts, split_hands_by_continuity, split_hands_viterbi, split_voices
from amt.quantizer import polyphony, quantize
from braille_translator.model import Rest


def resultado(*notas):
    return TranscriptionResult(notes=[NoteEvent(*n) for n in notas], duration_s=4.0)


class TestArmonicosDeOctava(unittest.TestCase):
    def test_quita_la_octava_mas_debil(self):
        r = drop_octave_ghosts(resultado((0.0, 1.0, 60, 90), (0.01, 1.0, 72, 40)))
        self.assertEqual([n.midi_pitch for n in r.notes], [60])

    def test_conserva_la_octava_tocada_con_fuerza(self):
        r = drop_octave_ghosts(resultado((0.0, 1.0, 60, 60), (0.01, 1.0, 72, 90)))
        self.assertEqual(len(r.notes), 2)

    def test_conserva_la_octava_que_entra_despues(self):
        r = drop_octave_ghosts(resultado((0.0, 1.0, 60, 90), (0.5, 1.0, 72, 40)))
        self.assertEqual(len(r.notes), 2)


class TestTrinos(unittest.TestCase):
    def test_trino_queda_como_nota_principal(self):
        notas = [(0.06 * k, 0.06 * k + 0.05, 67 if k % 2 == 0 else 69) for k in range(6)]
        r = collapse_trills(resultado(*notas))
        self.assertEqual([(n.midi_pitch, round(n.offset_s, 2)) for n in r.notes], [(67, 0.35)])

    def test_escala_lenta_no_se_toca(self):
        r = collapse_trills(resultado((0.0, 0.4, 60), (0.5, 0.9, 62), (1.0, 1.4, 60), (1.5, 1.9, 62)))
        self.assertEqual(len(r.notes), 4)


class TestRepartoDeManos(unittest.TestCase):
    def test_melodia_bajo_do4_sigue_en_la_derecha(self):
        notas = [NoteEvent(0.0, 0.5, 64), NoteEvent(0.0, 0.5, 48), NoteEvent(0.5, 1.0, 59), NoteEvent(0.5, 1.0, 45)]
        derecha, izquierda = split_hands_by_continuity(notas)
        self.assertEqual(sorted(n.midi_pitch for n in derecha), [59, 64])
        self.assertEqual(sorted(n.midi_pitch for n in izquierda), [45, 48])


class TestVoces(unittest.TestCase):
    def test_nota_larga_y_notas_rapidas_van_a_voces_distintas(self):
        notas = [NoteEvent(0.0, 2.0, 60), NoteEvent(0.0, 0.5, 67), NoteEvent(0.5, 1.0, 69), NoteEvent(1.0, 1.5, 71)]
        superior, inferior = split_voices(notas)
        self.assertEqual([n.midi_pitch for n in superior], [67, 69, 71])
        self.assertEqual([n.midi_pitch for n in inferior], [60])

    def test_cuantizador_escribe_la_segunda_voz_como_in_accord(self):
        r = resultado((0.0, 2.0, 60), (0.0, 0.5, 67), (0.5, 1.0, 69), (1.0, 1.5, 71), (1.5, 2.0, 72))
        compas = quantize(r, tempo_bpm=120, beats=4, beat_type=4, voices=("right",)).right.measures[0]
        self.assertEqual(len(compas.extra_voices), 1)
        self.assertTrue(all(not isinstance(e, Rest) for e in compas.events))

    def test_sin_polifonia_no_hay_in_accord(self):
        r = resultado((0.0, 0.5, 67), (0.5, 1.0, 69), (1.0, 1.5, 71), (1.5, 2.0, 72))
        compas = quantize(r, tempo_bpm=120, beats=4, beat_type=4, voices=("right",)).right.measures[0]
        self.assertEqual(compas.extra_voices, [])


class TestRepartoViterbi(unittest.TestCase):
    def test_mano_no_se_estira_mas_de_una_decima(self):
        notas = [NoteEvent(0.0, 0.5, p) for p in (40, 47, 60, 76)]
        derecha, izquierda = split_hands_viterbi(notas, span_weight=4.0)
        for mano in (derecha, izquierda):
            alturas = [n.midi_pitch for n in mano]
            self.assertLessEqual(max(alturas) - min(alturas), 16)

    def test_sin_penalizacion_es_el_reparto_por_continuidad(self):
        notas = [NoteEvent(0.0, 0.5, 64), NoteEvent(0.0, 0.5, 48), NoteEvent(0.5, 1.0, 59), NoteEvent(0.5, 1.0, 45)]
        self.assertEqual(split_hands_viterbi(notas, beam=1, span_weight=0.0), split_hands_by_continuity(notas))


class TestVocesAdaptativas(unittest.TestCase):
    def test_polifonia_por_compas(self):
        sostenida = [NoteEvent(0.0, 2.0, 60), NoteEvent(0.5, 1.0, 67), NoteEvent(1.0, 1.5, 69)]
        melodia = [NoteEvent(2.0 + 0.5 * k, 2.4 + 0.5 * k, 67 + k) for k in range(4)]
        puntaje = polyphony(sostenida + melodia, 0.25, 8)
        self.assertGreater(puntaje[0], 0.5)
        self.assertEqual(puntaje[1], 0.0)

    def test_compas_sin_polifonia_queda_sin_in_accord(self):
        notas = [NoteEvent(0.0, 2.0, 60), NoteEvent(0.0, 0.5, 67), NoteEvent(0.5, 1.0, 69), NoteEvent(1.0, 1.5, 71),
                 NoteEvent(1.5, 2.0, 72)] + [NoteEvent(2.0 + 0.5 * k, 2.4 + 0.5 * k, 67 + k) for k in range(4)]
        compases = quantize(resultado(*[(n.onset_s, n.offset_s, n.midi_pitch) for n in notas]), tempo_bpm=120,
                            voices=("right",), voice_threshold=0.5).right.measures
        self.assertEqual(len(compases[0].extra_voices), 1)
        self.assertEqual(compases[1].extra_voices, [])


class TestLigadurasPorLegato(unittest.TestCase):
    def test_notas_sin_separacion_llevan_ligadura(self):
        r = resultado((0.0, 0.5, 60), (0.5, 1.0, 62), (1.0, 1.5, 64), (1.6, 1.8, 65))
        eventos = quantize(r, tempo_bpm=120, slur_ratio=0.0).right.measures[0].events
        notas = [e for e in eventos if not isinstance(e, Rest)]
        self.assertEqual([n.slur for n in notas], [True, True, False, False])

    def test_mas_de_cuatro_notas_usa_apertura_y_cierre(self):
        r = resultado(*[(0.5 * k, 0.5 * k + 0.5, 60 + k) for k in range(6)])
        compases = quantize(r, tempo_bpm=120, beats=4, beat_type=4, slur_ratio=0.0).right.measures
        notas = [e for m in compases for e in m.events if not isinstance(e, Rest)]
        self.assertTrue(notas[0].slur_open)
        self.assertTrue(notas[5].slur_close)
        self.assertFalse(any(n.slur for n in notas))

    def test_apagado_por_omision(self):
        r = resultado((0.0, 0.5, 60), (0.5, 1.0, 62))
        self.assertFalse(any(getattr(e, "slur", False) for e in quantize(r, tempo_bpm=120).right.measures[0].events))


if __name__ == "__main__":
    unittest.main()
