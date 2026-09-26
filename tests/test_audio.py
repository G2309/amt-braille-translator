import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import numpy as np
    from amt.audio import PEAK_CEILING, TARGET_DBFS, active_rms, normalize_loudness
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def db(x):
    return 20 * np.log10(x)


@unittest.skipUnless(HAS_NUMPY, "numpy no instalado")
class TestNormalizeLoudness(unittest.TestCase):
    def tono(self, amp, seconds=2.0, sr=16000):
        t = np.arange(int(seconds * sr)) / sr
        return (amp * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_audio_bajo_sube_al_nivel_de_referencia(self):
        y = normalize_loudness(self.tono(0.001))
        self.assertAlmostEqual(db(active_rms(y)), TARGET_DBFS, delta=0.1)

    def test_audio_alto_baja_al_nivel_de_referencia(self):
        y = normalize_loudness(self.tono(0.9))
        self.assertAlmostEqual(db(active_rms(y)), TARGET_DBFS, delta=0.1)

    def test_no_recorta_picos(self):
        x = self.tono(0.01)
        x[1000] = 0.5
        y = normalize_loudness(x)
        self.assertLessEqual(np.abs(y).max(), PEAK_CEILING + 1e-6)

    def test_los_silencios_no_inflan_la_ganancia(self):
        x = np.concatenate([self.tono(0.1), np.zeros(16000 * 8, dtype=np.float32)])
        y = normalize_loudness(x)
        self.assertAlmostEqual(db(active_rms(y)), TARGET_DBFS, delta=0.5)

    def test_quita_componente_continua(self):
        y = normalize_loudness(self.tono(0.1) + 0.3)
        self.assertAlmostEqual(float(y.mean()), 0.0, places=4)

    def test_silencio_total_no_se_amplifica(self):
        x = np.zeros(16000, dtype=np.float32)
        self.assertTrue(np.array_equal(normalize_loudness(x), x))


if __name__ == "__main__":
    unittest.main()
