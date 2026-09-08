"""Consistencia entre la documentacion y el codigo.

El tercer objetivo especifico promete que cada regla del Manual sea trazable
hasta la prueba que la verifica. Esa correspondencia vive en los docs, asi que
conviene que algo la revise sola en lugar de confiar en revisarla a mano.
"""
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evaluation.bsa import CATEGORY_WEIGHTS

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
TESTS = RAIZ / "tests"

SUBSET = DOCS / "braille_rules_subset.md"
METRICA = DOCS / "bsa_metric.md"


def clases_definidas() -> set:
    encontradas = set()
    for archivo in TESTS.glob("test_*.py"):
        encontradas |= set(re.findall(r"^class (\w+)\(", archivo.read_text(encoding="utf-8"), re.M))
    return encontradas


def porcentajes(texto: str, encabezado: str) -> list:
    """Porcentajes de la tabla que sigue al encabezado indicado."""
    inicio = texto.index(encabezado)
    resto = texto[inicio:]
    fin = resto.find("\n## ", 1)
    bloque = resto if fin == -1 else resto[:fin]
    return [int(n) for n in re.findall(r"\|\s*(\d+)\s*%\s*\|", bloque)]


@unittest.skipUnless(SUBSET.exists(), "falta docs/braille_rules_subset.md")
class TestTrazabilidadConPruebas(unittest.TestCase):
    def setUp(self):
        self.texto = SUBSET.read_text(encoding="utf-8")

    def test_las_clases_citadas_en_los_docs_existen(self):
        citadas = set(re.findall(r"`(Test\w+)`", self.texto))
        self.assertTrue(citadas, "la tabla de trazabilidad no cita ninguna clase")
        faltantes = citadas - clases_definidas()
        self.assertFalse(faltantes, f"clases citadas que ya no existen: {sorted(faltantes)}")

    def test_los_archivos_de_prueba_citados_existen(self):
        citados = set(re.findall(r"`(test_\w+\.py)`", self.texto))
        faltantes = {n for n in citados if not (TESTS / n).exists()}
        self.assertFalse(faltantes, f"archivos citados que no existen: {sorted(faltantes)}")


@unittest.skipUnless(SUBSET.exists() and METRICA.exists(), "faltan documentos de docs/")
class TestPesosDelBsa(unittest.TestCase):
    def test_los_pesos_del_subset_suman_cien(self):
        pesos = porcentajes(SUBSET.read_text(encoding="utf-8"),
                            "## 10. Categorización de errores")
        self.assertEqual(len(pesos), len(CATEGORY_WEIGHTS))
        self.assertEqual(sum(pesos), 100)

    def test_los_dos_documentos_declaran_los_mismos_pesos(self):
        del_subset = sorted(porcentajes(SUBSET.read_text(encoding="utf-8"),
                                        "## 10. Categorización de errores"))
        de_la_metrica = sorted(porcentajes(METRICA.read_text(encoding="utf-8"),
                                           "## 4. BSA ponderado"))
        self.assertEqual(del_subset, de_la_metrica)

    def test_el_codigo_usa_esos_mismos_pesos(self):
        documentados = sorted(porcentajes(METRICA.read_text(encoding="utf-8"),
                                          "## 4. BSA ponderado"))
        en_codigo = sorted(round(p * 100) for p in CATEGORY_WEIGHTS.values())
        self.assertEqual(documentados, en_codigo)


if __name__ == "__main__":
    unittest.main()
