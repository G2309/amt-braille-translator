"""Pruebas de la API REST con un transcriptor simulado (sin PyTorch).

Se omiten si fastapi/httpx no estan instalados.
"""
import threading
import time
import unittest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from amt.events import NoteEvent, TranscriptionResult


class FakeTranscriber:
    """Devuelve una escala fija; permite bloquear para probar estados."""

    def __init__(self, gate: threading.Event = None, duration_s: float = 4.0):
        self.gate = gate
        self.duration_s = duration_s

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        if self.gate is not None:
            self.gate.wait(timeout=5)
        notes = [NoteEvent(onset_s=i * 0.5, offset_s=(i + 1) * 0.5, midi_pitch=60 + i)
                 for i in range(8)]
        return TranscriptionResult(notes=notes, duration_s=self.duration_s,
                                   source=audio_path, model_name="fake")


def wait_status(client, job_id, target="done", timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        data = client.get(f"/transcriptions/{job_id}").json()
        if data["status"] in (target, "error"):
            return data
        time.sleep(0.02)
    raise AssertionError(f"timeout esperando estado {target}: {data}")


@unittest.skipUnless(HAS_FASTAPI, "fastapi no instalado")
class TestApi(unittest.TestCase):
    def setUp(self):
        from api.app import create_app
        self.client = TestClient(create_app(transcriber_factory=FakeTranscriber))

    def _upload(self, name="audio.wav", **form):
        return self.client.post(
            "/transcriptions",
            files={"file": (name, b"RIFF0000WAVEfake", "audio/wav")},
            data=form,
        )

    def test_flujo_completo(self):
        r = self._upload()
        self.assertEqual(r.status_code, 202)
        job_id = r.json()["id"]

        data = wait_status(self.client, job_id)
        self.assertEqual(data["status"], "done")
        self.assertTrue(data["brf_valid"], data["brf_problems"])
        self.assertTrue(data["within_scope"])
        self.assertIsNotNone(data["latency_norm"])

        brf = self.client.get(f"/transcriptions/{job_id}/brf")
        self.assertEqual(brf.status_code, 200)
        cuerpo = brf.content.decode("ascii")
        self.assertTrue(all(len(l) <= 40 for l in cuerpo.replace("\f", "").split("\r\n")))

    def test_extension_no_soportada(self):
        r = self._upload(name="cancion.ogg")
        self.assertEqual(r.status_code, 415)

    def test_trabajo_inexistente(self):
        self.assertEqual(self.client.get("/transcriptions/nope").status_code, 404)
        self.assertEqual(self.client.get("/transcriptions/nope/brf").status_code, 404)

    def test_brf_antes_de_terminar_da_409(self):
        from api.app import create_app
        gate = threading.Event()
        client = TestClient(create_app(transcriber_factory=lambda: FakeTranscriber(gate=gate)))
        job_id = client.post(
            "/transcriptions",
            files={"file": ("a.wav", b"x", "audio/wav")},
        ).json()["id"]
        try:
            r = client.get(f"/transcriptions/{job_id}/brf")
            self.assertEqual(r.status_code, 409)
        finally:
            gate.set()
            wait_status(client, job_id)

    def test_audio_largo_queda_fuera_de_alcance(self):
        from api.app import create_app
        client = TestClient(create_app(
            transcriber_factory=lambda: FakeTranscriber(duration_s=400.0)))
        job_id = client.post(
            "/transcriptions", files={"file": ("a.wav", b"x", "audio/wav")},
        ).json()["id"]
        data = wait_status(client, job_id)
        self.assertEqual(data["status"], "done")
        self.assertFalse(data["within_scope"])

    def test_error_del_transcriptor_se_reporta(self):
        class Roto:
            def transcribe(self, path):
                raise RuntimeError("modelo no disponible")

        from api.app import create_app
        client = TestClient(create_app(transcriber_factory=Roto))
        job_id = client.post(
            "/transcriptions", files={"file": ("a.wav", b"x", "audio/wav")},
        ).json()["id"]
        data = wait_status(client, job_id, target="error")
        self.assertEqual(data["status"], "error")
        self.assertIn("RuntimeError", data["error"])
        self.assertEqual(client.get(f"/transcriptions/{job_id}/brf").status_code, 500)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn("model_available", r.json())


class TestValidateBrf(unittest.TestCase):
    def _write(self, content: bytes):
        import tempfile
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".brf")
        f.write(content)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_archivo_valido(self):
        from braille_translator.brf_exporter import validate_brf
        path = self._write(b'"?:$]\r\n_nr\r\n')
        self.assertEqual(validate_brf(path), [])

    def test_linea_larga_es_invalida(self):
        from braille_translator.brf_exporter import validate_brf
        path = self._write(b"a" * 41 + b"\r\n")
        problems = validate_brf(path)
        self.assertTrue(any("41" in p for p in problems))

    def test_no_ascii_es_invalido(self):
        from braille_translator.brf_exporter import validate_brf
        path = self._write("⠽⠵\r\n".encode("utf-8"))
        self.assertEqual(validate_brf(path), ["el archivo contiene bytes fuera de ASCII"])


if __name__ == "__main__":
    unittest.main()
