"""Pruebas unitarias del modulo de traduccion Braille.

Cada clase de prueba corresponde a una categoria sintactica del subset
(y por tanto a una categoria de error del BSA, seccion 10 del subset doc).
Ejecutar con:  python -m pytest tests/ -v o python -m unittest
"""
import unittest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from braille_translator import braille_tables as bt
from braille_translator.brf_exporter import wrap_line
from braille_translator.fsm import AccidentalState, OctaveState
from braille_translator.model import Chord, Hand, Measure, Note, Rest, Score
from braille_translator.renderer import render_bar_over_bar
from braille_translator.translator import HandTranslator, translate_score


def N(step, octave, dtype="quarter", alter=0, dots=0):
    return Note(step=step, octave=octave, duration_type=dtype, alter=alter, dots=dots)


class TestOctaveRules(unittest.TestCase):
    """Regla 1-10 — signos de octava segun distancia intervalica (US-08)."""

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
    """Seccion III.A — vigencia de alteraciones en el compas (US-09)."""

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
    """Regla 5-1 — nota principal e intervalos segun la mano (US-05)."""

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
    """Regla 5-2 — intervalos mayores que la octava (US-09)."""

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
    """Reglas 1-10 / 15-3 — signo de octava al inicio de cada renglon (US-08)."""

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
    """Reglas 14-17 / 14-22 — alineacion vertical y linea guia (US-10)."""

    def test_primer_signo_de_cada_compas_alineado(self):
        rh = ["\u2801\u2803\u2805", "\u2801"]
        lh = ["\u2801", "\u2801\u2803\u2805\u2807"]
        out = render_bar_over_bar(rh, lh, measures_per_line=2)
        lines = [l for l in out.split("\n") if l]
        # el segundo compas empieza en la misma columna en ambas manos
        self.assertEqual(lines[0].rindex("\u2800"), lines[1].rindex("\u2800"))

    def test_el_relleno_usa_linea_guia_de_punto_3(self):
        rh = ["\u2801\u2803\u2805", "\u2801"]
        lh = ["\u2801", "\u2801"]
        out = render_bar_over_bar(rh, lh, measures_per_line=2)
        lines = [l for l in out.split("\n") if l]
        self.assertIn(bt.DOT * 2, lines[1])   # mano corta rellenada con puntos 3

    def test_el_ultimo_compas_no_lleva_linea_guia(self):
        rh = ["\u2801", "\u2801\u2803\u2805"]
        lh = ["\u2801", "\u2801"]
        out = render_bar_over_bar(rh, lh, measures_per_line=2)
        lines = [l for l in out.split("\n") if l]
        self.assertNotIn(bt.DOT, lines[1].replace(bt.FINAL_BAR, ""))


class TestTies(unittest.TestCase):
    def test_nota_ligada_lleva_el_signo_despues_de_la_figura(self):
        t = HandTranslator(Score(), Hand("right"))
        salida = t.translate_measure(Measure(1, events=[N("C", 4, dtype="half")]))
        ligada = HandTranslator(Score(), Hand("right")).translate_measure(
            Measure(1, events=[Note("C", 4, "half", tie=True)])
        )
        self.assertEqual(ligada, salida + bt.TIE)

    def test_el_puntillo_precede_a_la_ligadura(self):
        t = HandTranslator(Score(), Hand("right"))
        salida = t.translate_measure(
            Measure(1, events=[Note("C", 4, "half", dots=1, tie=True)])
        )
        self.assertTrue(salida.endswith(bt.DOT + bt.TIE))

    def test_acorde_entero_ligado_usa_el_signo_de_acorde(self):
        # Regla 6-12: acorde completo prolongado -> ligadura de acorde
        t = HandTranslator(Score(), Hand("right"))
        acorde = Chord(notes=[N("C", 4), N("E", 4)], duration_type="quarter", tie=True)
        salida = t.translate_measure(Measure(1, events=[acorde]))
        self.assertTrue(salida.endswith(bt.CHORD_TIE))
        self.assertNotIn(bt.TIE, salida)

    def test_acorde_ligado_no_duplica_la_ligadura_de_la_nota_principal(self):
        # Los miembros del acorde del cuantizador tambien llevan tie=True;
        # con chord.tie solo debe emitirse la ligadura de acorde.
        t = HandTranslator(Score(), Hand("right"))
        miembros = [Note("C", 4, "quarter", tie=True), Note("E", 4, "quarter", tie=True)]
        acorde = Chord(notes=miembros, duration_type="quarter", tie=True)
        salida = t.translate_measure(Measure(1, events=[acorde]))
        self.assertEqual(salida.count(bt.CHORD_TIE), 1)
        self.assertNotIn(bt.TIE, salida)

    def test_ligadura_de_una_sola_nota_del_acorde(self):
        # Regla 6-11: la ligadura de nota unica va tras la nota o intervalo
        t = HandTranslator(Score(), Hand("right"))
        miembros = [Note("C", 4, "quarter", tie=True), Note("E", 4, "quarter")]
        acorde = Chord(notes=miembros, duration_type="quarter")
        salida = t.translate_measure(Measure(1, events=[acorde]))
        self.assertTrue(salida.endswith(bt.INTERVAL[3] + bt.TIE))
        self.assertNotIn(bt.CHORD_TIE, salida)


class TestInAccords(unittest.TestCase):
    """Voces simultaneas de una misma mano separadas por cópula."""

    def _dos_voces(self):
        return Measure(1, events=[N("C", 4, "half")], extra_voices=[[N("E", 4, "half")]])

    def test_las_voces_se_separan_con_el_signo_de_copula(self):
        t = HandTranslator(Score(), Hand("right"))
        self.assertIn(bt.IN_ACCORD, t.translate_measure(self._dos_voces()))

    def test_la_primera_nota_de_la_segunda_voz_lleva_octava(self):
        t = HandTranslator(Score(), Hand("right"))
        _, segunda = t.translate_measure(self._dos_voces()).split(bt.IN_ACCORD)
        self.assertTrue(segunda.startswith(bt.OCTAVE_SIGN[4]))

    def test_sin_voces_extra_no_aparece_copula(self):
        t = HandTranslator(Score(), Hand("right"))
        salida = t.translate_measure(Measure(1, events=[N("C", 4)]))
        self.assertNotIn(bt.IN_ACCORD, salida)

    def test_la_segunda_voz_no_hereda_la_altura_de_la_primera(self):
        # Ambas voces parten de la misma referencia de entrada al compas.
        m = Measure(1, events=[N("C", 4, "half"), N("B", 6, "half")],
                    extra_voices=[[N("D", 4, "half")]])
        t = HandTranslator(Score(), Hand("right"))
        _, segunda = t.translate_measure(m).split(bt.IN_ACCORD)
        self.assertTrue(segunda.startswith(bt.OCTAVE_SIGN[4]))


class TestSlurs(unittest.TestCase):
    """Reglas 6-2 / 6-3(b) / 6-8 — ligaduras de expresion (US-11)."""

    def test_ligadura_corta_tras_cada_nota_menos_la_ultima(self):
        # Regla 6-2
        t = HandTranslator(Score(), Hand("right"))
        notas = [Note("C", 4, "quarter", slur=True),
                 Note("D", 4, "quarter", slur=True),
                 Note("E", 4, "quarter")]
        salida = t.translate_measure(Measure(1, events=notas))
        self.assertEqual(salida.count(bt.SLUR), 2)
        self.assertFalse(salida.endswith(bt.SLUR))

    def test_ligadura_larga_usa_apertura_y_cierre(self):
        # Regla 6-3(b)
        t = HandTranslator(Score(), Hand("right"))
        notas = [Note("C", 4, "quarter", slur_open=True)] + [
            N(s, 4) for s in "DEFG"
        ] + [Note("A", 4, "quarter", slur_close=True)]
        salida = t.translate_measure(Measure(1, events=notas))
        self.assertTrue(salida.startswith(bt.SLUR_OPEN))
        self.assertTrue(salida.endswith(bt.SLUR_CLOSE))
        self.assertNotIn(bt.SLUR, salida.replace(bt.SLUR_OPEN, "").replace(bt.SLUR_CLOSE, ""))

    def test_en_acordes_la_ligadura_va_antes_de_los_intervalos(self):
        # Regla 6-8 (uso de España)
        t = HandTranslator(Score(), Hand("right"))
        acorde = Chord(notes=[N("C", 4), N("E", 4)], duration_type="quarter", slur=True)
        salida = t.translate_measure(Measure(1, events=[acorde]))
        self.assertTrue(salida.endswith(bt.SLUR + bt.INTERVAL[3]))

    def test_la_ligadura_de_expresion_precede_a_la_de_prolongacion(self):
        # Regla 6-9
        t = HandTranslator(Score(), Hand("right"))
        nota = Note("C", 4, "quarter", slur=True, tie=True)
        salida = t.translate_measure(Measure(1, events=[nota]))
        self.assertTrue(salida.endswith(bt.SLUR + bt.TIE))


class TestInAccordAccidentals(unittest.TestCase):
    """Regla 5-14 — las alteraciones no sobreviven al signo de cópula."""

    def test_la_segunda_voz_reemite_la_alteracion(self):
        m = Measure(1, events=[N("F", 4, "half", alter=1), N("F", 4, "half", alter=1)],
                    extra_voices=[[N("F", 4, "half", alter=1)]])
        t = HandTranslator(Score(), Hand("right"))
        primera, segunda = t.translate_measure(m).split(bt.IN_ACCORD)
        self.assertEqual(primera.count(bt.ACCIDENTAL[1]), 1)
        self.assertEqual(segunda.count(bt.ACCIDENTAL[1]), 1)


class TestTieContinuationAccidental(unittest.TestCase):
    """Regla 6-10 — alteracion de nota ligada al compas siguiente."""

    def _score(self):
        score = Score()
        score.right.measures = [
            Measure(1, events=[Note("F", 4, "whole", alter=1, tie=True)]),
            Measure(2, events=[Note("F", 4, "whole", alter=1, tie_from_prev=True)]),
        ]
        score.left.measures = [
            Measure(1, events=[N("C", 3, "whole")]),
            Measure(2, events=[N("C", 3, "whole")]),
        ]
        return score

    def test_continuacion_en_el_mismo_renglon_no_repite_alteracion(self):
        rh, _ = translate_score(self._score(), measures_per_line=4)
        self.assertNotIn(bt.ACCIDENTAL[1], rh[1])

    def test_continuacion_en_renglon_nuevo_si_repite_alteracion(self):
        rh, _ = translate_score(self._score(), measures_per_line=1)
        self.assertIn(bt.ACCIDENTAL[1], rh[1])

    def test_la_alteracion_queda_vigente_para_el_resto_del_compas(self):
        score = self._score()
        # tras la continuacion ligada, otro Fa en el mismo compas no la repite
        score.right.measures[1].events.append(N("F", 4, alter=1))
        rh, _ = translate_score(score, measures_per_line=4)
        self.assertNotIn(bt.ACCIDENTAL[1], rh[1])


class TestKeySignature(unittest.TestCase):
    """Regla 3-3 — armadura de la clave."""

    def test_sin_alteraciones_no_emite_nada(self):
        self.assertEqual(bt.key_signature(0), "")

    def test_hasta_tres_repite_el_signo(self):
        self.assertEqual(bt.key_signature(2), bt.ACCIDENTAL[1] * 2)
        self.assertEqual(bt.key_signature(-3), bt.ACCIDENTAL[-1] * 3)

    def test_cuatro_o_mas_usa_numero_y_signo(self):
        self.assertEqual(bt.key_signature(-4),
                         bt.NUMBER_SIGN + bt.UPPER_DIGIT[4] + bt.ACCIDENTAL[-1])


class TestBarSigns(unittest.TestCase):
    """Tabla 9 A — barra final y doble barra de fin de seccion."""

    def test_barra_final_y_doble_barra_son_distintas(self):
        self.assertNotEqual(bt.FINAL_BAR, bt.DOUBLE_BAR)

    def test_puntos_verificados_contra_la_tabla_9a(self):
        self.assertEqual(bt.FINAL_BAR, bt.cell(1, 2, 6) + bt.cell(1, 3))
        self.assertEqual(bt.DOUBLE_BAR, bt.cell(1, 2, 6) + bt.cell(1, 3) + bt.cell(3))


class TestMusicXMLLigaduras(unittest.TestCase):
    """Parser: <tie> y <notations><slur> -> campos del AST."""

    HEADER = """<?xml version="1.0"?>
<score-partwise><part id="P1"><measure number="1">
<attributes><key><fifths>0</fifths></key>
<time><beats>4</beats><beat-type>4</beat-type></time></attributes>
{notes}
</measure></part></score-partwise>"""

    def _nota(self, step, extra=""):
        return (f"<note><pitch><step>{step}</step><octave>4</octave></pitch>"
                f"<duration>1</duration><type>quarter</type>{extra}</note>")

    def _parse(self, notes_xml):
        import tempfile
        from braille_translator.musicxml_parser import parse_musicxml
        with tempfile.NamedTemporaryFile("w", suffix=".musicxml", delete=False) as f:
            f.write(self.HEADER.format(notes=notes_xml))
            path = f.name
        try:
            return parse_musicxml(path)
        finally:
            os.unlink(path)

    def test_tie_start_y_stop(self):
        score = self._parse(
            self._nota("C", '<tie type="start"/>') + self._nota("C", '<tie type="stop"/>')
        )
        eventos = score.right.measures[0].events
        self.assertTrue(eventos[0].tie)
        self.assertTrue(eventos[1].tie_from_prev)

    def test_ligadura_corta_marca_todas_menos_la_ultima(self):
        notas = (self._nota("C", '<notations><slur type="start"/></notations>')
                 + self._nota("D")
                 + self._nota("E", '<notations><slur type="stop"/></notations>'))
        eventos = self._parse(notas).right.measures[0].events
        self.assertEqual([e.slur for e in eventos], [True, True, False])

    def test_ligadura_larga_marca_apertura_y_cierre(self):
        notas = (self._nota("C", '<notations><slur type="start"/></notations>')
                 + self._nota("D") + self._nota("E") + self._nota("F")
                 + self._nota("G", '<notations><slur type="stop"/></notations>'))
        eventos = self._parse(notas).right.measures[0].events
        self.assertTrue(eventos[0].slur_open)
        self.assertTrue(eventos[-1].slur_close)
        self.assertFalse(any(e.slur for e in eventos))


class TestBrfWrap(unittest.TestCase):
    def test_no_parte_un_compas_a_la_mitad(self):
        linea = " ".join(["cccc"] * 12)
        for l in wrap_line(linea, width=40):
            self.assertLessEqual(len(l), 40)
            self.assertNotIn("  c", l.strip())

    def test_la_continuacion_va_sangrada(self):
        linea = " ".join(["cccc"] * 12)
        salida = wrap_line(linea, width=40)
        self.assertGreater(len(salida), 1)
        self.assertTrue(salida[1].startswith("  "))

    def test_linea_corta_no_se_toca(self):
        self.assertEqual(wrap_line("abc", width=40), ["abc"])

    def test_compas_mas_largo_que_la_linea_se_corta_duro(self):
        salida = wrap_line("c" * 95, width=40)
        self.assertTrue(all(len(l) <= 40 for l in salida))
        self.assertEqual("".join(l.strip() for l in salida), "c" * 95)


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
