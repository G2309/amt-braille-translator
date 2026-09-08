"""Pruebas del calculo de BSA.

La estrategia es inyectar errores conocidos sobre una salida correcta y
comprobar que el modulo los detecta, los cuenta y los atribuye a la categoria
que corresponde.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from braille_translator import braille_tables as bt
from braille_translator.model import Hand, Measure, Note, Score
from braille_translator.translator import translate_score
from evaluation.bsa import (
    CATEGORY_WEIGHTS, classify_cells, compute_bsa, load_braille,
)


def N(step, octave, dtype="quarter", alter=0):
    return Note(step=step, octave=octave, duration_type=dtype, alter=alter)


class TestClassify(unittest.TestCase):
    def test_signo_de_mano_ocupa_dos_celdas_de_su_categoria(self):
        celdas = classify_cells(bt.RIGHT_HAND)
        self.assertEqual([c for _, c in celdas], ["manos", "manos"])

    def test_ligadura_de_prolongacion_no_se_parte_en_octava_mas_signo(self):
        # ⠈⠉ empieza con el signo de 1a octava; el simbolo largo debe ganar
        celdas = classify_cells(bt.TIE)
        self.assertEqual([c for _, c in celdas], ["ligaduras", "ligaduras"])

    def test_doble_barra_gana_sobre_barra_final_mas_puntillo(self):
        celdas = classify_cells(bt.DOUBLE_BAR)
        self.assertEqual([c for _, c in celdas], ["barras"] * 3)

    def test_signo_de_numero_al_inicio_no_es_intervalo(self):
        celdas = classify_cells(bt.time_signature(4, 4))
        self.assertEqual(celdas[0][1], "alteraciones")

    def test_misma_celda_tras_una_nota_es_intervalo_de_cuarta(self):
        texto = bt.note_cell("C", "quarter") + bt.INTERVAL[4]
        celdas = classify_cells(texto)
        self.assertEqual([c for _, c in celdas], ["notas", "intervalos"])

    def test_las_cifras_del_compas_no_se_confunden_con_notas(self):
        # los digitos comparten celda con las corcheas; manda el signo de numero
        celdas = classify_cells(bt.time_signature(4, 4))
        self.assertEqual([c for _, c in celdas], ["alteraciones"] * 3)

    def test_puntillo_tras_nota_cuenta_como_nota(self):
        celdas = classify_cells(bt.note_cell("C", "half") + bt.DOT)
        self.assertEqual([c for _, c in celdas], ["notas", "notas"])

    def test_punto_3_de_relleno_cuenta_como_bar_over_bar(self):
        celdas = classify_cells(bt.BAR + bt.DOT)
        self.assertEqual([c for _, c in celdas], ["barras", "bar_over_bar"])

    def test_octava_y_alteracion(self):
        texto = bt.ACCIDENTAL[1] + bt.OCTAVE_SIGN[4] + bt.note_cell("F", "quarter")
        self.assertEqual([c for _, c in classify_cells(texto)],
                         ["alteraciones", "octavas", "notas"])


class TestBsaScoring(unittest.TestCase):
    def setUp(self):
        self.ref = (bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter")
                    + bt.note_cell("D", "quarter") + bt.BAR
                    + bt.note_cell("E", "quarter"))

    def test_identicos_dan_bsa_perfecto(self):
        r = compute_bsa(self.ref, self.ref)
        self.assertEqual(r.bsa, 1.0)
        self.assertEqual(r.substitutions + r.deletions + r.insertions, 0)

    def test_octava_omitida_es_una_omision_en_octavas(self):
        hyp = self.ref.replace(bt.OCTAVE_SIGN[4], "", 1)
        r = compute_bsa(self.ref, hyp)
        self.assertEqual(r.deletions, 1)
        self.assertEqual(r.per_category["octavas"].deletions, 1)
        self.assertEqual(r.per_category["octavas"].bsa, 0.0)

    def test_nota_cambiada_es_una_sustitucion_en_notas(self):
        hyp = self.ref.replace(bt.note_cell("D", "quarter"),
                               bt.note_cell("G", "quarter"), 1)
        r = compute_bsa(self.ref, hyp)
        self.assertEqual(r.substitutions, 1)
        self.assertEqual(r.per_category["notas"].substitutions, 1)

    def test_barra_de_mas_es_una_insercion_en_barras(self):
        hyp = self.ref + bt.BAR
        r = compute_bsa(self.ref, hyp)
        self.assertEqual(r.insertions, 1)
        self.assertEqual(r.per_category["barras"].insertions, 1)

    def test_el_bsa_baja_en_proporcion_a_las_celdas_erroneas(self):
        hyp = self.ref.replace(bt.OCTAVE_SIGN[4], "", 1)
        r = compute_bsa(self.ref, hyp)
        self.assertAlmostEqual(r.bsa, 4 / 5)

    def test_referencia_vacia_contra_salida_no_vacia(self):
        r = compute_bsa("", self.ref)
        self.assertEqual(r.bsa, 0.0)
        self.assertEqual(r.insertions, len(self.ref))

    def test_ambas_vacias(self):
        self.assertEqual(compute_bsa("", "").bsa, 1.0)

    def test_los_totales_cuadran_con_las_celdas(self):
        hyp = self.ref.replace(bt.note_cell("D", "quarter"), "", 1) + bt.BAR
        r = compute_bsa(self.ref, hyp)
        self.assertEqual(r.matches + r.substitutions + r.deletions, r.total_ref)
        self.assertEqual(r.matches + r.substitutions + r.insertions, r.total_hyp)


class TestWeightedBsa(unittest.TestCase):
    def test_los_pesos_del_subset_suman_uno(self):
        self.assertAlmostEqual(sum(CATEGORY_WEIGHTS.values()), 1.0)

    def test_solo_pesan_las_categorias_presentes(self):
        # sin in-accords ni ligaduras, un texto perfecto sigue dando 100%
        ref = bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter")
        self.assertAlmostEqual(compute_bsa(ref, ref).weighted_bsa, 1.0)

    def test_un_fallo_en_categoria_pesada_baja_mas_que_en_una_ligera(self):
        ref = (bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter") + bt.BAR
               + bt.OCTAVE_SIGN[5] + bt.note_cell("D", "quarter") + bt.BAR)
        sin_octava = ref.replace(bt.OCTAVE_SIGN[5], "", 1)   # octavas, peso 0.20
        sin_barra = ref[:-1]                                  # barras, peso 0.05
        self.assertLess(compute_bsa(ref, sin_octava).weighted_bsa,
                        compute_bsa(ref, sin_barra).weighted_bsa)


class TestBrfRoundTrip(unittest.TestCase):
    def test_ida_y_vuelta_conserva_las_celdas(self):
        original = bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter") + bt.BAR
        self.assertEqual(bt.brf_to_unicode(bt.unicode_to_brf(original)), original)

    def test_brf_en_mayusculas_se_interpreta_igual(self):
        original = bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter")
        ascii_txt = bt.unicode_to_brf(original)
        self.assertEqual(bt.brf_to_unicode(ascii_txt.upper()), original)

    def test_load_braille_acepta_archivo_brf(self):
        original = bt.OCTAVE_SIGN[4] + bt.note_cell("C", "quarter")
        f = tempfile.NamedTemporaryFile("w", suffix=".brf", delete=False, encoding="ascii")
        f.write(bt.unicode_to_brf(original))
        f.close()
        self.addCleanup(os.unlink, f.name)
        self.assertEqual(load_braille(f.name), original)


class TestBsaSobreSalidaReal(unittest.TestCase):
    """Sobre una partitura traducida por el propio sistema."""

    def _score(self):
        score = Score()
        for i in (1, 2):
            score.right.measures.append(
                Measure(i, events=[N("C", 4), N("E", 4), N("G", 4), N("C", 5)]))
            score.left.measures.append(Measure(i, events=[N("C", 3, "whole")]))
        return score

    def test_una_partitura_contra_si_misma_da_cien_por_ciento(self):
        rh, lh = translate_score(self._score())
        texto = "\n".join(rh + lh)
        r = compute_bsa(texto, texto)
        self.assertEqual(r.bsa, 1.0)
        self.assertEqual(r.weighted_bsa, 1.0)

    def test_no_quedan_celdas_sin_clasificar(self):
        rh, lh = translate_score(self._score())
        categorias = {c for _, c in classify_cells("\n".join(rh + lh))}
        self.assertNotIn("desconocido", categorias)

    def test_el_reporte_menciona_las_categorias_presentes(self):
        rh, lh = translate_score(self._score())
        texto = "\n".join(rh + lh)
        reporte = compute_bsa(texto, texto).report()
        self.assertIn("BSA global", reporte)
        self.assertIn("notas", reporte)
        self.assertIn("octavas", reporte)


if __name__ == "__main__":
    unittest.main()
