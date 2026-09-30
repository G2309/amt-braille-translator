# Resultados

Datos que respaldan el capítulo de Resultados, uno o más archivos por objetivo. Los CSV guardan una fila por obra o pieza y condición, sin las notas crudas; las figuras se generan con `notebooks/resultados-figuras.ipynb`.

| Archivo | Objetivo | Origen |
| --- | --- | --- |
| `oe1_benchmark_por_obra.csv` | OE1 | Kaggle `amt-benchmark-ipynb`, versión 3 (`notebooks/amt-benchmark-full.ipynb`) |
| `oe2_robustez_por_obra.csv` | OE2 | Kaggle `amt-robustness`, versión 2 |
| `oe2_ajuste_por_obra.csv` | OE2 | Kaggle `amt-finetune`, versión 3 |
| `oe2_ajuste_validacion.json` | OE2 | Kaggle `amt-finetune`, versión 3 |
| `oe4_latencia_e2e.csv` | OE4 | Kaggle `amt-latency-e2e`, versión 1 |
| `oe5_notas/` | OE5 | Kaggle `amt-goldberg-transcribe`, versión 1 |
| `oe5_bsa_por_pieza.csv`, `oe5_bsa_por_categoria.csv` | OE5 | `notebooks/amt-bsa-goldberg.ipynb`, local |
| `figuras/` | todos | `notebooks/resultados-figuras.ipynb`, local |

La referencia Braille del quinto objetivo es la edición en musicografía Braille de las Open Goldberg Variations, y el audio es la grabación de Kimiko Ishizaka del mismo proyecto, publicadas bajo licencia Creative Commons Zero. La referencia no se guarda en el repositorio: el notebook la descarga de https://opengoldbergvariations.org.
