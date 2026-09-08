# amt-braille-translator

[![pruebas](https://github.com/G2309/amt-braille-translator/actions/workflows/tests.yml/badge.svg)](https://github.com/G2309/amt-braille-translator/actions/workflows/tests.yml)

Convierte grabaciones de piano polifónico en partituras de musicografía Braille listas para leer en una línea Braille o imprimir en un embosser.

El problema que resuelve está en el hueco entre dos tecnologías maduras que nunca se hablaron. Los modelos de Transcripción Musical Automática terminan su trabajo entregando un MIDI, y los traductores a Braille empiezan el suyo exigiendo una partitura digital ya estructurada. Entre ese punto final y ese punto de partida hay un tramo que hasta ahora recaía sobre el propio músico invidente, obligado a encadenar herramientas que no fueron diseñadas para comunicarse. Este proyecto cubre ese tramo completo, de audio a archivo BRF, sin intervención manual.

Trabajo de graduación · Universidad del Valle de Guatemala · Gustavo Cruz Bardales

## El pipeline

```mermaid
flowchart TD
    A["Audio de piano<br/>MP3 · WAV · FLAC · hasta 5 min"]

    subgraph IA["Etapa probabilística — inteligencia artificial"]
        B["AMTTranscriber<br/>Kong et al. 2021"]
        C["TranscriptionResult<br/>notas con onset, offset, altura y velocidad<br/>+ pedal de resonancia"]
    end

    subgraph DET["Etapa determinista — reglas del Manual de la ONCE"]
        D["Cuantizador rítmico<br/>grilla de semicorchea · acordes · separación de manos"]
        E["AST<br/>Score → Hand → Measure → Note · Chord · Rest"]
        F["Traductor + máquina de estados<br/>signos de octava · alteraciones vigentes"]
        G["Renderizador compás sobre compás<br/>alineación vertical de ambas manos"]
        H["Exportador BRF<br/>40 celdas por línea · 25 líneas por página"]
    end

    I[("archivo .brf")]
    J["Validación sintáctica"]
    K["BSA contra referencia humana"]

    A --> B --> C --> D --> E --> F --> G --> H --> I
    I --> J
    I --> K
```

La separación en dos etapas es la decisión de diseño central del proyecto, no un detalle de implementación. La transcripción acústica es un problema probabilístico donde un error del 3 % se considera un resultado excelente; la musicografía Braille es un terreno determinista donde un solo punto omitido en un signo de octava altera el significado de toda una frase. Un modelo generativo entrenado para producir Braille directamente tendería a inventar notaciones inválidas con apariencia correcta, y la normativa no admite ese comportamiento. Por eso la IA se queda en la etapa acústica y la traducción se resuelve con reglas auditables contra un texto normativo.

## Qué hace y qué no

Procesa piano polifónico a dos manos y produce un archivo BRF conforme al subconjunto de veintiocho reglas, en nueve secciones, del *Manual Simplificado de Musicografía Braille* (Aller Pérez, ONCE, 2001). Ese subconjunto abarca notas y silencios, signos de octava, alteraciones y su vigencia dentro del compás, intervalos armónicos, in-accords, ligaduras de expresión y de prolongación, barras de compás, formato compás sobre compás y signos de mano.

Queda fuera del alcance el audio con voz cantada u otros instrumentos, la notación visual en pentagrama, la edición interactiva del Braille, el procesamiento en tiempo real y las reglas avanzadas del Manual como ornamentos, matices detallados y signos de pedal en su notación Braille propia. El detalle completo, con su justificación técnica, está en [`docs/braille_rules_subset.md`](docs/braille_rules_subset.md).

## Instalación

```bash
git clone <repo> && cd amt-braille-translator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

El checkpoint del modelo acústico se descarga solo la primera vez que se transcribe audio.

## Uso

**De audio a BRF**, que es el flujo del sistema.

```python
from pipeline import audio_to_brf
audio_to_brf("nocturno.wav", "nocturno.brf", tempo_bpm=60, beats=4, beat_type=4)
```

**Como API REST.**

```bash
uvicorn api.app:app --app-dir src
```

| Método | Ruta | Qué hace |
| --- | --- | --- |
| `POST` | `/transcriptions` | recibe el audio y encola el trabajo, devuelve su id |
| `GET` | `/transcriptions/{id}` | estado, latencia normalizada y validez del BRF |
| `GET` | `/transcriptions/{id}/brf` | descarga el archivo resultante |
| `GET` | `/health` | disponibilidad del servicio y del modelo |

**Medir la calidad del resultado** contra una transcripción de referencia.

```bash
PYTHONPATH=src python -m evaluation referencia.brf generado.brf
```

Devuelve la Exactitud de Símbolo Braille global y ponderada, con el desglose de aciertos, sustituciones, omisiones e inserciones por categoría sintáctica.

### Banco de pruebas del traductor

La entrada del sistema es audio. Aun así, el repositorio incluye un lector de MusicXML que alimenta directamente el árbol de sintaxis abstracta, saltándose la etapa acústica. Sirve para ejercitar y depurar la traducción Braille con una partitura de contenido conocido, sin GPU ni modelo, y es lo que usan buena parte de las pruebas. No forma parte del alcance del producto.

```bash
python run_demo.py examples/simple_piece.musicxml salida.brf
```

## Arquitectura

| Módulo | Responsabilidad |
| --- | --- |
| `src/amt/transcriber.py` | envoltura del modelo acústico; aísla PyTorch del resto |
| `src/amt/events.py` | contrato de datos entre las dos etapas |
| `src/amt/quantizer.py` | tiempos continuos a figuras rítmicas, acordes y manos |
| `src/braille_translator/model.py` | árbol de sintaxis abstracta de la partitura |
| `src/braille_translator/fsm.py` | contexto de octavas y alteraciones |
| `src/braille_translator/translator.py` | recorrido del árbol y emisión de celdas |
| `src/braille_translator/renderer.py` | formato compás sobre compás |
| `src/braille_translator/brf_exporter.py` | exportación y validación del BRF |
| `src/braille_translator/braille_tables.py` | tablas de símbolos cotejadas con el Manual |
| `src/api/` | API REST asíncrona |
| `src/evaluation/bsa.py` | métrica de exactitud sobre el Braille final |

El árbol de sintaxis abstracta cumple una función muy concreta. El formato compás sobre compás exige que las barras de ambas manos queden alineadas verticalmente, y como todas las celdas Braille ocupan el mismo ancho, no hay forma de decidir el relleno sin saber de antemano cuánto va a medir cada uno de los dos compases. Ese cálculo anticipado solo es posible teniendo la obra entera representada en memoria antes de emitir el primer carácter.

## Pruebas

```bash
python -m unittest discover -s tests
```

146 pruebas. Las de la API se omiten solas si FastAPI no está instalado. La correspondencia entre cada regla del Manual y la prueba que la verifica está en la sección de trazabilidad de [`docs/braille_rules_subset.md`](docs/braille_rules_subset.md), y hay pruebas que verifican que esa tabla siga siendo cierta.

Cada push a `dev` o `main` dispara el workflow de GitHub Actions, que corre la suite en Python 3.10, 3.12 y 3.13, traduce la partitura de ejemplo comprobando que el BRF resultante sea válido, mide la latencia de la etapa determinista y verifica que los notebooks estén bien formados.

## Documentación

- [`docs/braille_rules_subset.md`](docs/braille_rules_subset.md) — las veintiocho reglas implementadas, con su numeración original del Manual y su trazabilidad con el código y las pruebas.
- [`docs/bsa_metric.md`](docs/bsa_metric.md) — procedimiento de medición de la Exactitud de Símbolo Braille.
- [`docs/literature_review_amt.md`](docs/literature_review_amt.md) — revisión de modelos de transcripción y benchmark comparativo.
- [`notebooks/amt-benchmark-full.ipynb`](notebooks/amt-benchmark-full.ipynb) — benchmark reproducible sobre veinte obras completas de MAESTRO v3.0.0.
- [`notebooks/latency-e2e.ipynb`](notebooks/latency-e2e.ipynb) — medición de latencia del pipeline completo, de audio a BRF.

## Selección del modelo acústico

Estos son los resultados sobre veinte obras completas de la partición de prueba de MAESTRO v3.0.0, medidos con `mir_eval`.

| Modelo | F1 onset | F1 nota (con offset) | NER | Latencia normalizada |
| --- | :---: | :---: | :---: | :---: |
| Kong et al. (2021) | 95.89 % | 83.74 % | 8.01 % | 0.097 |
| hFT-Transformer (2023) | 96.68 % | 89.30 % | 6.36 % | 0.079 |
| Basic Pitch (2022) | 64.75 % | 19.46 % | 63.37 % | 0.030 |

El sistema integra a **Kong et al. (2021)**. hFT-Transformer obtiene mejores métricas de nota, pero no detecta el pedal de resonancia, y su ventaja está en la precisión del offset, que el cuantizador rítmico absorbe al ajustar las duraciones a la grilla. Queda documentado como la extensión natural del sistema.

## Licencia

GPL-3.0. El proyecto se construye íntegramente sobre tecnología de código abierto para que pueda auditarse y extenderse sin costos de licenciamiento.

## Referencias

Aller Pérez, J. (2001). *Manual simplificado de musicografía braille: Versión para usuarios no ciegos*. ONCE.

Kong, Q., Li, B., Song, X., Wan, Y., & Wang, Y. (2021). High-resolution piano transcription with pedals by regressing onset and offset times. *IEEE/ACM TASLP, 29*, 3707–3717.

Krolick, B. (1998). *Nuevo manual internacional de musicografía braille* (F. J. Martínez Calvo, Trad.). ONCE.
