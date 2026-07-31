"""Pruebas unitarias del modulo de traduccion Braille.

Cada clase de prueba corresponde a una categoria sintactica del subset
(y por tanto a una categoria de error del BSA, seccion 10 del subset doc).
Ejecutar con:  python -m pytest tests/ -v o python -m unittest
"""
import unittest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from braille_translator import braille_tables as bt
from braille_translator.fsm import AccidentalState, OctaveState
from braille_translator.model import Chord, Hand, Measure, Note, Rest, Score
from braille_translator.renderer import render_bar_over_bar
from braille_translator.translator import HandTranslator, translate_score


def N(step, octave, dtype="quarter", alter=0, dots=0):
    return Note(step=step, octave=octave, duration_type=dtype, alter=alter, dots=dots)


class TestOctaveRules(unittest.TestCase):
    """Regla 2-3 — signos de octava segun distancia intervalica (US-08)."""

    def setUp(self):
        self.fsm = OctaveState()

    def test_primera_nota_siempre_lleva_octava(self):
        self.assertTrue(self.fsm.needs_octave_sign(N("C", 4)))

    def test_intervalo_de_segunda_no_lleva_octava(self):
        self.fsm.needs_octave_sign(N("C", 4))
        self.assertFalse(self.fsm.needs_octave_sign(N("D", 4)))

    def test_intervalo_de_tercera_no_lleva_octava(self):
        self.fsm.needs_octave_sign(N("C", 4))
        self.assertFalse(self.fsm.needs_octave_sign(N("E", 4)))

    def test_cuarta_misma_octava_no_lleva(self):
        self.fsm.needs_octave_sign(N("C", 4))
        self.assertFalse(self.fsm.needs_octave_sign(N("F", 4)))

    def test_quinta_cruzando_octava_si_lleva(self):
        self.fsm.needs_octave_sign(N("A", 4))
        self.assertTrue(self.fsm.needs_octave_sign(N("E", 5)))

    def test_sexta_siempre_lleva_aunque_sea_misma_octava(self):
        self.fsm.needs_octave_sign(N("C", 4))
        self.assertTrue(self.fsm.needs_octave_sign(N("A", 4)))


class TestAccidentalRules(unittest.TestCase):
    """Reglas 3-2 / 3-3 — vigencia de alteraciones en el compas (US-09)."""

    def test_alteracion_se_emite_una_vez_por_compas(self):
        fsm = AccidentalState({})
        fsm.start_measure()
        self.assertEqual(fsm.accidental_to_emit(N("C", 5, alter=1)), 1)
        self.assertIsNone(fsm.accidental_to_emit(N("C", 5, alter=1)))

    def test_becuadro_cancela_alteracion_vigente(self):
        fsm = AccidentalState({})
        fsm.start_measure()
        fsm.accidental_to_emit(N("C", 5, alter=1))
        self.assertEqual(fsm.accidental_to_emit(N("C", 5, alter=0)), 0)

    def test_armadura_no_reemite_en_notas_afectadas(self):
        fsm = AccidentalState({"F": 1})     # 1 sostenido (Fa#)
        fsm.start_measure()
        self.assertIsNone(fsm.accidental_to_emit(N("F", 4, alter=1)))

    def test_becuadro_contra_armadura(self):
        fsm = AccidentalState({"F": 1})
        fsm.start_measure()
        self.assertEqual(fsm.accidental_to_emit(N("F", 4, alter=0)), 0)

    def test_reset_por_compas(self):
        fsm = AccidentalState({})
        fsm.start_measure()
        fsm.accidental_to_emit(N("G", 4, alter=-1))
        fsm.start_measure()
        self.assertEqual(fsm.accidental_to_emit(N("G", 4, alter=-1)), -1)

    def test_misma_letra_distinta_octava_requiere_emision(self):
        fsm = AccidentalState({})
        fsm.start_measure()
        fsm.accidental_to_emit(N("C", 4, alter=1))
        self.assertEqual(fsm.accidental_to_emit(N("C", 5, alter=1)), 1)


class TestChordIntervals(unittest.TestCase):
    """Reglas 5-1 / 5-2 — nota principal e intervalos segun la mano (US-05)."""

    def test_mano_derecha_principal_es_la_mas_aguda(self):
        chord = Chord(notes=[N("C", 4), N("E", 4), N("G", 4)], duration_type="half")
        self.assertEqual(chord.principal("right").step, "G")

    def test_mano_izquierda_principal_es_la_mas_grave(self):
        chord = Chord(notes=[N("C", 3), N("G", 3)], duration_type="half")
        self.assertEqual(chord.principal("left").step, "C")

    def test_orden_intervalos_mano_derecha_descendente(self):
        chord = Chord(notes=[N("C", 4), N("E", 4), N("G", 4)], duration_type="half")
        secundarias = [n.step for n in chord.secondary("right")]
        self.assertEqual(secundarias, ["E", "C"])


class TestCompoundIntervals(unittest.TestCase):
    """Regla 5-1b — intervalos mayores que la octava (US-09)."""

    def _traducir(self, notas, side="left"):
        t = HandTranslator(Score(), Hand(side))
        return t.translate_measure(Measure(1, events=[
            Chord(notes=notas, duration_type="quarter")
        ]))

    def test_novena_lleva_signo_de_octava_antes_del_intervalo(self):
        salida = self._traducir([N("C", 4), N("D", 5)])
        self.assertEqual(salida[-2:], bt.OCTAVE_SIGN[5] + bt.INTERVAL[2])

    def test_novena_no_se_confunde_con_segunda(self):
        novena = self._traducir([N("C", 4), N("D", 5)])
        segunda = self._traducir([N("C", 5), N("D", 5)])
        self.assertNotEqual(novena[1:], segunda[1:])

    def test_quincena_no_se_confunde_con_octava(self):
        quincena = self._traducir([N("C", 4), N("C", 6)])
        octava = self._traducir([N("C", 4), N("C", 5)])
        self.assertEqual(quincena[-2:], bt.OCTAVE_SIGN[6] + bt.INTERVAL[8])
        self.assertEqual(octava[-1:], bt.INTERVAL[8])

    def test_octava_justa_no_lleva_signo_de_octava(self):
        salida = self._traducir([N("C", 4), N("C", 5)])
        self.assertEqual(salida, bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter") + bt.INTERVAL[8])


class TestLineBreakOctave(unittest.TestCase):
    """Reglas 2-2 / 15-2 — signo de octava al inicio de cada renglon (US-08)."""

    def _score_repetido(self, n_compases):
        score = Score()
        for i in range(1, n_compases + 1):
            score.right.measures.append(Measure(i, events=[N("C", 4, "whole")]))
            score.left.measures.append(Measure(i, events=[N("C", 3, "whole")]))
        return score

    def test_primer_compas_de_cada_renglon_lleva_octava(self):
        rh, lh = translate_score(self._score_repetido(6), measures_per_line=4)
        self.assertTrue(rh[0].startswith(bt.OCTAVE_SIGN[4]))
        self.assertTrue(rh[4].startswith(bt.OCTAVE_SIGN[4]))
        self.assertTrue(lh[4].startswith(bt.OCTAVE_SIGN[3]))

    def test_compas_interior_del_renglon_no_reemite_octava(self):
        rh, _ = translate_score(self._score_repetido(6), measures_per_line=4)
        for i in (1, 2, 3, 5):
            self.assertFalse(rh[i].startswith(bt.OCTAVE_SIGN[4]), f"compas {i}")

    def test_renglon_respeta_measures_per_line_configurado(self):
        rh, _ = translate_score(self._score_repetido(6), measures_per_line=2)
        for i in (0, 2, 4):
            self.assertTrue(rh[i].startswith(bt.OCTAVE_SIGN[4]), f"compas {i}")


class TestBarOverBar(unittest.TestCase):
    """Regla 14-2 — alineacion vertical (US-10)."""

    def test_compases_alineados_al_mismo_ancho(self):
        rh = ["\u2801\u2803\u2805", "\u2801"]                
        lh = ["\u2801", "\u2801\u2803\u2805\u2807"]         
        out = render_bar_over_bar(rh, lh, measures_per_line=2)
        lines = [l for l in out.split("\n") if l]
        body_rh = lines[0][3:]
        body_lh = lines[1][3:]
        self.assertEqual(len(body_rh), len(body_lh))


class TestBrfMapping(unittest.TestCase):
    """US-07 — exportacion BRF valida."""

    def test_celda_do_negra_mapea_a_ascii(self):
        do_negra = bt.note_cell("C", "quarter")
        ascii_out = bt.unicode_to_brf(do_negra)
        self.assertEqual(len(ascii_out), 1)
        self.assertTrue(ascii_out.isascii())

    def test_espacio_braille_mapea_a_espacio(self):
        self.assertEqual(bt.unicode_to_brf("\u2800"), " ")


class TestEndToEnd(unittest.TestCase):
    """Prueba de integracion: AST manual -> traduccion completa."""

    def test_score_minimo(self):
        score = Score(beats=4, beat_type=4, fifths=0)
        m_rh = Measure(1, events=[N("C", 4), N("D", 4), N("E", 4), Rest("quarter")])
        m_lh = Measure(1, events=[N("C", 3, "whole")])
        score.right.measures.append(m_rh)
        score.left.measures.append(m_lh)

        rh, lh = translate_score(score)
        self.assertEqual(len(rh), 1)
        self.assertEqual(len(lh), 1)
        self.assertTrue(rh[0].startswith(bt.OCTAVE_SIGN[4]))
        self.assertTrue(lh[0].startswith(bt.OCTAVE_SIGN[3]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
