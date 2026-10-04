import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import convertir


class TestArgumentos(unittest.TestCase):
    def test_compas(self):
        self.assertEqual(convertir.leer_compas("3/4"), (3, 4))
        self.assertEqual(convertir.leer_compas("6/8"), (6, 8))

    def test_compas_invalido(self):
        for texto in ("3-4", "0/4", "3/5"):
            with self.assertRaises(argparse.ArgumentTypeError):
                convertir.leer_compas(texto)

    def test_valores_por_omision(self):
        a = convertir.argumentos(["pieza.m4a"])
        self.assertEqual((a.tempo, a.compas, a.armadura, a.modelo), (60.0, (4, 4), 0, "ajustado"))
        self.assertFalse(a.voces or a.ligaduras or a.tempo_fijo)


class TestConversion(unittest.TestCase):
    def test_formatos_directos_no_se_convierten(self):
        for ext in (".mp3", ".WAV", ".flac"):
            self.assertEqual(convertir.a_wav(Path("pieza" + ext), Path(".")), Path("pieza" + ext))

    def test_m4a_sin_ffmpeg_avisa(self):
        with mock.patch("convertir.shutil.which", return_value=None), self.assertRaises(SystemExit):
            convertir.a_wav(Path("pieza.m4a"), Path(tempfile.gettempdir()))

    def test_m4a_pasa_por_ffmpeg(self):
        with mock.patch("convertir.shutil.which", return_value="/usr/bin/ffmpeg"), \
             mock.patch("convertir.subprocess.run") as run:
            destino = convertir.a_wav(Path("grabacion.m4a"), Path("/tmp/x"))
        self.assertEqual(destino, Path("/tmp/x/grabacion.wav"))
        self.assertEqual(run.call_args[0][0][0], "ffmpeg")


if __name__ == "__main__":
    unittest.main()
