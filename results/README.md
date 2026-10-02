# Resultados

Datos que respaldan el capítulo de Resultados, uno o más archivos por objetivo. Los CSV guardan una fila por obra o pieza y condición, sin las notas crudas; las figuras se generan con `notebooks/resultados-figuras.ipynb`.

| Archivo | Objetivo | Origen |
| --- | --- | --- |
| `oe1_benchmark_por_obra.csv` | OE1 | Kaggle `amt-benchmark-ipynb`, versión 3 (`notebooks/amt-benchmark-full.ipynb`) |
| `oe2_robustez_por_obra.csv` | OE2 | Kaggle `amt-robustness`, versión 2 |
| `oe2_ajuste_por_obra.csv` | OE2 | Kaggle `amt-finetune`, versión 3 |
| `oe2_ajuste_validacion.json` | OE2 | Kaggle `amt-finetune`, versión 3 |
| `oe4_latencia_e2e.csv` | OE4 | Kaggle `amt-latency-e2e`, versión 1 |
| `oe4_latencia_cpu.csv` | OE4 | `scripts/latencia_cpu.py`, local en CPU (Ryzen 7 5700X) con 2, 4 y 8 núcleos |
| `oe5_notas/` | OE5 | Kaggle `amt-goldberg-transcribe`, versión 1 |
| `oe5_bsa_por_pieza.csv`, `oe5_bsa_por_categoria.csv` | OE5 | `notebooks/amt-bsa-goldberg.ipynb`, local |
| `oe5_externo_notas/` | OE5 | Kaggle `amt-externo-transcribe`, versión 1 |
| `oe5_ablacion_desarrollo.csv`, `oe5_prueba_y_externo.csv`, `oe5_techo_traductor.csv` | OE5 | `notebooks/amt-bsa-mejoras.ipynb`, local |
| `figuras/` | todos | `notebooks/resultados-figuras.ipynb`, local |

La referencia Braille del quinto objetivo es la edición en musicografía Braille de las Open Goldberg Variations, y el audio es la grabación de Kimiko Ishizaka del mismo proyecto, publicadas bajo licencia Creative Commons Zero. La referencia no se guarda en el repositorio: el notebook la descarga de https://opengoldbergvariations.org.

Las mejoras del quinto objetivo se eligen solo con la partición de desarrollo de Goldberg (Aria, variaciones 1 a 15 y Aria da capo) y se miden una vez en la de prueba (variaciones 16 a 30 sin la 25) y en tres obras externas. Las referencias externas son ediciones compás sobre compás de la biblioteca BrailleOrch (Bor001, Bor195 y Bor343) y las grabaciones son de dominio público o CC0 en Internet Archive. El techo del traductor usa la partitura MusicXML de las Open Goldberg Variations, de la misma edición que la referencia Braille, descargada de http://open-goldberg.oankali.net.

La latencia en CPU complementa la medida en GPU. Se usaron cortes de 30, 60, 120 y 300 segundos formados con las grabaciones de Für Elise y del vals de Chopin del conjunto externo, y el pipeline completo con sus valores por omisión. Con 2 núcleos, que es lo que ofrece el plan gratuito de Hugging Face Spaces, el cociente máximo fue 1.21 y quedó dentro del umbral de 1.5; los doce BRF fueron válidos y la memoria máxima fue de 1.2 GB.
