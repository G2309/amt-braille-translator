import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from amt.beats import beat_unit_quarters, follow_tempo, track_beats, warp_to_score
from amt.events import NoteEvent, TranscriptionResult
from amt.quantizer import quantize


def ataques(tiempos, altura=60):
    return [NoteEvent(t, t + 0.1, altura, 80) for t in tiempos]


# Bajo en cada pulso y cuatro semicorcheas arriba, como en una textura de teclado
def textura(pulsos):
    notas = []
    for t, siguiente in zip(pulsos, pulsos[1:]):
        d = siguiente - t
        notas.append(NoteEvent(t, siguiente, 48, 90))
        notas += [NoteEvent(t + j * d / 4, t + (j + 1) * d / 4, 67 + j, 70) for j in range(4)]
    return notas


def tiempos(intervalo, n=25):
    out, t = [], 0.0
    for k in range(n):
        out.append(t)
        t += intervalo(k)
    return out


class TestUnidad(unittest.TestCase):
    def test_negra_en_cuartos_y_corchea_en_octavos(self):
        self.assertEqual(beat_unit_quarters(4), 1.0)
        self.assertEqual(beat_unit_quarters(2), 1.0)
        self.assertEqual(beat_unit_quarters(8), 0.5)


class TestSeguimiento(unittest.TestCase):
    def test_pulso_regular(self):
        pulsos = track_beats(ataques([0.5 * k for k in range(12)]), 0.5)
        self.assertEqual(len(pulsos), 12)
        self.assertTrue(all(abs(p - 0.5 * k) < 0.02 for k, p in enumerate(pulsos)))

    def test_accelerando_no_pierde_ni_agrega_pulsos(self):
        reales = tiempos(lambda k: 0.6 - 0.2 * k / 23)
        pulsos = track_beats(textura(reales), 0.5)
        self.assertIn(len(pulsos), (24, 25))
        self.assertTrue(all(abs(p - q) < 0.03 for p, q in zip(pulsos, reales[:24])))

    def test_primer_pulso_en_el_primer_ataque(self):
        pulsos = track_beats(ataques([2.0 + 0.5 * k for k in range(8)]), 0.5)
        self.assertAlmostEqual(pulsos[0], 2.0, places=2)


class TestDeformacion(unittest.TestCase):
    def test_interpola_entre_pulsos_y_extrapola_al_final(self):
        r = TranscriptionResult(notes=[NoteEvent(0.3, 1.5, 60)], duration_s=2.0)
        w = warp_to_score(r, [0.0, 0.6, 1.0], 1.0)
        self.assertAlmostEqual(w.notes[0].onset_s, 0.5)
        self.assertAlmostEqual(w.notes[0].offset_s, 3.25)

    def test_ritardando_queda_en_la_grilla(self):
        reales = tiempos(lambda k: 0.5 + 0.2 * max(0, k - 11) / 12)
        r = TranscriptionResult(notes=textura(reales), duration_s=reales[-1])
        w = follow_tempo(r, 120.0, 4)
        bajos = [n.onset_s for n in w.notes if n.midi_pitch == 48]
        self.assertTrue(all(abs(b - k) < 0.2 for k, b in enumerate(bajos)))
        compases = quantize(w, tempo_bpm=60.0, beats=4, beat_type=4).right.measures
        self.assertEqual(len(compases), 6)

    def test_silencio_inicial_se_conserva(self):
        r = TranscriptionResult(notes=ataques([1.0 + 0.5 * k for k in range(8)]), duration_s=5.0)
        w = follow_tempo(r, 120.0, 4)
        self.assertAlmostEqual(w.notes[0].onset_s, 2.0, places=1)


if __name__ == "__main__":
    unittest.main()
