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
from evaluation.reference_eval import evaluate_piece, shifted_result

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
