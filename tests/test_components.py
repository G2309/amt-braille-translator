import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from braille_translator import braille_tables as bt
from evaluation.components import note_f1_by_measure, pitch_and_rhythm, read_pitches, strip_phrasing


def u(brf):
    return bt.brf_to_unicode(brf)


class TestLectorDeAlturas(unittest.TestCase):
    def test_octava_por_proximidad(self):
        # Sol4, Fa, Sol, Sol, Re, Mi, Fa, Sol, La, Si, Do5 en el primer compas de la Variacion 1
        alturas = [p for p, _ in read_pitches(u('"(=h@c(efg(ij%d'), "right")]
        self.assertEqual(alturas, [32, 31, 32, 32, 29, 30, 31, 32, 33, 34, 35])

    def test_salto_de_sexta_lleva_signo_y_se_respeta(self):
        celdas = bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter") + bt.OCTAVE_SIGN[4] + bt.note_cell("A", "quarter")
        self.assertEqual([p for p, _ in read_pitches(celdas, "right")], [28, 33])

    def test_intervalo_baja_en_derecha_y_sube_en_izquierda(self):
        acorde = bt.OCTAVE_SIGN[4] + bt.note_cell("E", "quarter") + bt.INTERVAL[3]
        self.assertEqual([p for p, _ in read_pitches(acorde, "right")], [30, 28])
        self.assertEqual([p for p, _ in read_pitches(acorde, "left")], [30, 32])


class TestDesglose(unittest.TestCase):
    def test_misma_altura_distinta_figura(self):
        ref = bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter") + bt.note_cell("D", "quarter")
        gen = bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter") + bt.note_cell("D", "half")
        self.assertEqual(pitch_and_rhythm((ref, ""), (gen, "")), (1.0, 0.5))

    def test_f1_por_compas_ignora_el_orden(self):
        a = bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter") + bt.note_cell("E", "quarter")
        b = bt.OCTAVE_SIGN[4] + bt.note_cell("E", "quarter") + bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter")
        self.assertEqual(note_f1_by_measure([(a, "")], [(b, "")]), 1.0)

    def test_quitar_fraseo_conserva_la_prolongacion(self):
        nota = bt.note_cell("C", "quarter")
        celdas = bt.SLUR_OPEN + nota + bt.SLUR + nota + bt.TIE + nota + bt.SLUR_CLOSE
        self.assertEqual(strip_phrasing(celdas), nota + nota + bt.TIE + nota)


if __name__ == "__main__":
    unittest.main()
