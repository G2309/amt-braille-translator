import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from amt.events import NoteEvent, TranscriptionResult
from amt.postprocess import collapse_trills, drop_octave_ghosts, split_hands_by_continuity, split_voices
from amt.quantizer import quantize
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


if __name__ == "__main__":
    unittest.main()
