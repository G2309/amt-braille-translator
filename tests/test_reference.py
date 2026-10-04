import os
import sys
import unittest
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from amt.quantizer import quantize
from braille_translator.braille_tables import unicode_to_brf
from braille_translator.translator import translate_score
from evaluation.reference import (
    Measure, clean, expand_repeats, parse_reference, parse_signature, reference_streams,
)
from evaluation.reference_eval import estimate_tempo, evaluate_piece, place_pickup, shifted_result

LETTERS = "jabcdefghi"


def numero(n: int) -> str:
    return "".join(LETTERS[int(d)] for d in str(n))


def edicion(rh, lh, cabecera="%#c4"):
    """BRF con el formato de la edicion: titulo, encabezado y una paralela por compas."""
    lineas = ["             aria4", f"         _a ;7#gb4 {cabecera}"]
    for i, (d, iz) in enumerate(zip(rh, lh), start=1):
        lineas.append(f"{numero(i)} .>{unicode_to_brf(d)}")
        lineas.append(f"  _>{unicode_to_brf(iz)}")
    return "\r\n".join(lineas) + "\r\n"


class TestParseSignature(unittest.TestCase):
    def test_compases_numericos(self):
        self.assertEqual(parse_signature("%#c4"), (1, 3, 4))
        self.assertEqual(parse_signature("%#ab16"), (1, 12, 16))

    def test_armadura_menor_con_becuadro(self):
        self.assertEqual(parse_signature("*<<#b4"), (-2, 2, 4))

    def test_compasillo_y_partido(self):
        self.assertEqual(parse_signature("%.c"), (1, 4, 4))
        self.assertEqual(parse_signature("%_c"), (1, 2, 2))


class TestParseReference(unittest.TestCase):
    BRF = (
        "              #a\r\n"
        "             aria4\r\n"
        "         _a ;7#gb4 %#c4\r\n"
        "a .>.\\\\ci')\r\n"
        " a_>_r'<>v_t\r\n"
        "b .>\"wwc%d'z ''''''' z%dji\r\n"
        " c_>_r'@c _\\/gfgj\r\n"
        "d .>.f\"5zcd\r\n"
        "    \"5)c['%.g\r\n"
        "  _>_n@cde\r\n"
    )

    def test_encabezado_y_numeracion(self):
        (pieza,) = parse_reference(self.BRF)
        self.assertEqual((pieza.fifths, pieza.beats, pieza.beat_type), (1, 3, 4))
        self.assertEqual([m.number for m in pieza.measures], [1, 2, 3, 4])

    def test_dos_compases_en_una_paralela_sin_relleno(self):
        (pieza,) = parse_reference(self.BRF)
        self.assertEqual(pieza.measures[1].right, "\"wwc%d'z")
        self.assertEqual(pieza.measures[2].right, "z%dji")
        self.assertEqual(pieza.measures[2].left, "_\\/gfgj")

    def test_linea_de_continuacion(self):
        (pieza,) = parse_reference(self.BRF)
        self.assertEqual(pieza.measures[3].right, ".f\"5zcd\"5)c['%.g")


# Formato de BrailleOrch: obra unica, columnas alineadas y palabras de expresion
class TestFormatoAlineado(unittest.TestCase):
    BRF = (
        "     ,poco moto4 #c8\r\n"
        "j .>'<7>pp.&%z &%ef\"j*ed\r\n"
        "  _>'<7   x    m\r\n"
        "b .>'>un peu anim=> \"p#*0\r\n"
        "  _>^p'<>^j)\r\n"
        "c .>'>mouvt 7sans lourdeuir7>\r\n"
        "     >pp;b\"j'9--\r\n"
        "  _>;b^h'9\r\n"
    )

    def setUp(self):
        (self.pieza,) = parse_reference(self.BRF)

    def test_obra_unica_con_anacrusa(self):
        self.assertEqual(self.pieza.title, "obra")
        self.assertEqual((self.pieza.beats, self.pieza.beat_type), (3, 8))
        self.assertTrue(self.pieza.has_pickup)
        self.assertEqual([m.number for m in self.pieza.measures], [0, 1, 2, 3])

    def test_mano_izquierda_por_columna(self):
        self.assertEqual(self.pieza.measures[0].left, "<7x")
        self.assertEqual(self.pieza.measures[1].left, "m")

    def test_palabras_y_matices_fuera(self):
        self.assertEqual(self.pieza.measures[0].right, "<7.&%z")
        self.assertEqual(self.pieza.measures[2].right, "\"p#*0")
        self.assertEqual(self.pieza.expressions, 4)

    def test_linea_solo_con_palabras_abre_compas(self):
        self.assertEqual(self.pieza.measures[3].right, ";b\"j'9--")
        self.assertEqual(self.pieza.measures[3].left, ";b^h'9")

    def test_armadura_numerica(self):
        self.assertEqual(parse_signature("?7#ff #f<#c4"), (-6, 3, 4))
        self.assertEqual(parse_signature("#d%.c"), (4, 4, 4))


# Obras con varios movimientos y da capo al fine, como en las sonatinas y el minueto de BrailleOrch
class TestMovimientos(unittest.TestCase):
    BRF = (
        "    ,moderato  %.c\r\n"
        "a .>\"r5jich\r\n"
        "  _>_r+q9\r\n"
        "b .>.dfc$<2\r\n"
        "  _>_s9<2\r\n"
        "\r\n"
        "                ,romanze \r\n"
        "\r\n"
        "    #f8\r\n"
        "a .>\"jcdcec\r\n"
        "  _>_hc8j\r\n"
        "\r\n"
        "     ,vivace4  #c8\r\n"
        "a .>.dbc8\r\n"
        "  _>_d1fbh\r\n"
        "b'.>'<7.i\"1x\r\n"
        "  _>_r+q9\r\n"
    )

    def setUp(self):
        self.piezas = parse_reference(self.BRF)

    def test_un_movimiento_por_encabezado(self):
        self.assertEqual([p.title for p in self.piezas], ["obra", "romanze", "vivace"])
        self.assertEqual([(p.beats, p.beat_type) for p in self.piezas], [(4, 4), (6, 8), (3, 8)])

    def test_armadura_heredada_solo_sin_compas_en_el_encabezado(self):
        self.assertEqual([p.fifths for p in self.piezas], [1, 1, 0])

    def test_numero_de_compas_con_apostrofo(self):
        self.assertEqual(len(self.piezas[2].measures), 2)
        self.assertTrue(self.piezas[2].measures[1].begins_repeat)

    def test_encabezado_con_numero_de_pieza(self):
        brf = ("    #b4\r\na .>\"r5j\r\n  _>_r+\r\n\r\n          #b4 ,allegro\r\n\r\n    #b4\r\na .>.dfc\r\n  _>_s9\r\n")
        self.assertEqual(len(parse_reference(brf)), 2)

    def test_da_capo_al_fine(self):
        brf = ("    ,allegretto  %#c4\r\n"
               "a .>\"r5j\r\n  _>_r+\r\n"
               "b .>.dfc$>fine\r\n  _>_s9\r\n"
               "c .>\"jcd\r\n  _>_hc\r\n"
               "d .>.ech>d'c' al fine>\r\n  _>_d1\r\n")
        (pieza,) = parse_reference(brf)
        self.assertTrue(pieza.da_capo)
        self.assertEqual([m.number for m in reference_streams(pieza).played], [1, 2, 3, 4, 1, 2])
        self.assertEqual(len(reference_streams(pieza, repeats=False).played), 4)


class TestPedal(unittest.TestCase):
    def test_signos_de_pedal_se_quitan(self):
        quitadas = Counter()
        self.assertEqual(clean("<c^!*c", quitadas), clean("^!", Counter()))
        self.assertEqual(quitadas["<c"] + quitadas["*c"], 2)


class TestRepeticiones(unittest.TestCase):
    def test_dos_secciones_repetidas(self):
        ms = [Measure(1, "a"), Measure(2, "b<2"), Measure(3, "<7c"), Measure(4, "d<2")]
        self.assertEqual([m.number for m in expand_repeats(ms)], [1, 2, 1, 2, 3, 4, 3, 4])

    def test_casillas_de_primera_y_segunda_vez(self):
        ms = [Measure(1, "a"), Measure(2, "#1b<2"), Measure(3, "#2c")]
        ms[1].right = "#1b<2"
        self.assertEqual([m.number for m in expand_repeats(ms)], [1, 2, 1, 3])

    def test_sin_repeticiones_queda_igual(self):
        ms = [Measure(i, "a") for i in range(1, 4)]
        self.assertEqual([m.number for m in expand_repeats(ms)], [1, 2, 3])


class TestLimpieza(unittest.TestCase):
    def test_quita_repeticiones_y_signos_desconocidos(self):
        quitados = Counter()
        limpio = clean("<7.d8e<2", quitados)
        self.assertEqual(quitados["<7"], 1)
        self.assertEqual(quitados["<2"], 1)
        self.assertEqual(quitados["8"], 1)
        self.assertNotIn("⠦", limpio)


# Anacrusa de una negra en 3/4 a 60 negras por minuto
class TestAnacrusa(unittest.TestCase):
    def setUp(self):
        from amt.events import NoteEvent, TranscriptionResult
        from evaluation.reference import Piece
        self.pieza = Piece(index=0, title="obra", beats=3, beat_type=4)
        notas = [NoteEvent(0.0, 0.9, 64), NoteEvent(1.0, 1.9, 69), NoteEvent(4.0, 4.9, 69)]
        self.resultado = TranscriptionResult(notes=notas, duration_s=5.0)

    def test_tempo_cuenta_solo_la_anacrusa(self):
        self.assertAlmostEqual(estimate_tempo(self.resultado, self.pieza, 3, pickup_quarters=1.0), 60.0)

    def test_anacrusa_ocupa_el_final_del_compas(self):
        movido = place_pickup(self.resultado, self.pieza, 60.0, 1.0)
        self.assertEqual([n.onset_s for n in movido.notes], [2.0, 3.0, 6.0])

    def test_sin_anacrusa_no_mueve(self):
        self.assertIs(place_pickup(self.resultado, self.pieza, 60.0, 0.0), self.resultado)


class TestIdaYVuelta(unittest.TestCase):
    """Si las notas son las de la partitura, el BSA tiene que dar 1."""

    def notas(self):
        escala = [60, 62, 64, 65, 67, 69, 71, 72, 74]
        notas, t = [], 0.5
        for i, p in enumerate(escala):
            notas.append([t, t + 0.9, p, 80])
            notas.append([t, t + 0.9, p - 24, 80])
            t += 1.0
        notas.append([t, t + 2.9, 60, 80])
        notas.append([t, t + 2.9, 36, 80])
        return notas

    def test_bsa_perfecto_con_la_partitura_de_referencia(self):
        notas = self.notas()
        result = shifted_result(notas, duration_s=12.0)
        score = quantize(result, tempo_bpm=60, beats=3, beat_type=4, fifths=0)
        rh, lh = translate_score(score, measures_per_line=1)
        (pieza,) = parse_reference(edicion(rh, lh, cabecera="#c4"))
        ev = evaluate_piece(pieza, notas, duration_s=12.0, repeats=False)
        self.assertAlmostEqual(ev.tempo_bpm, 60.0, places=3)
        self.assertEqual(ev.both.bsa, 1.0)

    def test_una_nota_equivocada_baja_el_bsa(self):
        notas = self.notas()
        result = shifted_result(notas, duration_s=12.0)
        score = quantize(result, tempo_bpm=60, beats=3, beat_type=4, fifths=0)
        rh, lh = translate_score(score, measures_per_line=1)
        (pieza,) = parse_reference(edicion(rh, lh, cabecera="#c4"))
        notas[4][2] += 2
        ev = evaluate_piece(pieza, notas, duration_s=12.0, repeats=False)
        self.assertLess(ev.both.bsa, 1.0)
        self.assertGreater(ev.both.bsa, 0.8)

    def test_reference_streams_cuenta_compases_tocados(self):
        notas = self.notas()
        score = quantize(shifted_result(notas, 12.0), tempo_bpm=60, beats=3, beat_type=4)
        rh, lh = translate_score(score, measures_per_line=1)
        (pieza,) = parse_reference(edicion(rh, lh, cabecera="#c4"))
        self.assertEqual(reference_streams(pieza).measures_played, len(rh))


if __name__ == "__main__":
    unittest.main()
