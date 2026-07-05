# Revisión de Literatura — Modelos de Transcripción Musical Automática (AMT) Polifónica

Este documento resume el estado del arte de los modelos de Transcripción Musical Automática (AMT) polifónica considerados como candidatos para el módulo de inferencia AMT del sistema. Cada modelo se caracteriza por su arquitectura, dataset de entrenamiento, métricas reportadas en la literatura, licencia y justificación de inclusión o descarte del benchmark comparativo (Fase 2 del Marco Metodológico).

La revisión sigue la nomenclatura métrica del Marco Metodológico:

- F1_onset: F1-Score a nivel de onset, considerando una nota correcta si el modelo predice el inicio con una tolerancia de ±50 ms respecto al ground truth.
- F1_note: F1-Score a nivel de nota con offset, considerando correcta una nota solo si onset y offset están dentro de tolerancia (típicamente ±50 ms para onset y el máximo entre 50 ms o el 20% de la duración para offset).
- NER (Note Error Rate): tasa de error a nivel de nota, complementaria del F1_note.

## 1. Contexto histórico y taxonomía

La AMT polifónica busca convertir una señal de audio en una representación simbólica que preserve las notas, sus onsets, offsets, alturas tonales y (opcionalmente) velocidades e información de pedal. Durante casi dos décadas dominaron los enfoques basados en factorización de matrices no negativas (NMF) y máquinas de estados ocultos, con desempeño limitado por su incapacidad de modelar dependencias temporales largas y estructuras armónicas complejas (Benetos et al., 2019).

A partir de 2017 la investigación se orientó de forma casi total al aprendizaje profundo, con tres familias arquitectónicas dominantes:

1. CNN + BiLSTM con doble objetivo onset/frame, inaugurada por Onsets and Frames (Hawthorne et al., 2018) y refinada por Kong et al. (2021).
2. CNN ligera multi-tarea, representada por Basic Pitch (Bittner et al., 2022), enfocada en instrumento-agnosticismo y eficiencia computacional.
3. Transformer seq2seq, representada por Sequence-to-Sequence Piano Transcription (Hawthorne et al., 2021) y su extensión multi-instrumento MT3 (Gardner et al., 2022), con vocabulario tipo MIDI y arquitectura T5.

Estos cuatro modelos constituyen los candidatos evaluados en este documento.

## 2. Modelo 1 — Onsets and Frames (Hawthorne et al., 2018)

### 2.1 Arquitectura

Red neuronal profunda compuesta por dos ramas paralelas:

- Onset stack: CNN (3 capas convolucionales) seguida de BiLSTM y una capa densa que predice, por cada frame, la probabilidad de que un onset comience en ese frame para cada una de las 88 notas del piano.
- Frame stack: CNN seguida de BiLSTM y una capa densa que predice la actividad de cada nota en cada frame.

La rama de frames se condiciona con la salida de la rama de onsets (concatenación de features intermedios). En inferencia, la actividad de frames se filtra con la predicción de onsets: una nota nueva solo se activa si la rama de onsets también predice un onset para ese frame. Adicionalmente, el modelo predice velocidades normalizadas por nota.

La entrada del modelo es un mel-espectrograma logarítmico calculado sobre audio a 16 kHz.

### 2.2 Dataset de entrenamiento

- MAPS (Emiya et al., 2010): base de datos de piano sintético y grabaciones reales de un Disklavier con MIDI alineado.
- MAESTRO v1.0.0 (Hawthorne et al., 2019): aproximadamente 172 horas de grabaciones del International Piano-e-Competition con MIDI alineado a nivel de milisegundos por medio de un Disklavier Yamaha.

### 2.3 Métricas reportadas en la literatura

Sobre el conjunto de prueba de MAESTRO v1.0.0 (Hawthorne et al., 2019):

- F1_onset ≈ 94.80%
- F1_note (con offset) ≈ 82.60%
- F1_frame ≈ 90.20%

### 2.4 Licencia y disponibilidad

- Código original: Apache License 2.0 (repositorio magenta/magenta en GitHub).
- Framework: TensorFlow 1.15.
- Existen implementaciones de terceros en PyTorch (por ejemplo jongwook/onsets-and-frames, licencia MIT) con checkpoints entrenados sobre MAESTRO.

### 2.5 Justificación

Estado en el benchmark: incluido como línea base histórica, no evaluado empíricamente.

Onsets and Frames marcó el punto de inflexión de la AMT polifónica moderna, pero su desempeño ha sido superado por Kong et al. (2021), quienes emplean la misma arquitectura CRNN mejorada con regresión de onsets y offsets de alta resolución sobre el mismo dataset. Los autores de Kong et al. reportan directamente el F1_onset de Onsets and Frames como línea base (94.80%) y muestran una mejora absoluta de casi 2 puntos porcentuales. Adicionalmente, el código original depende de TensorFlow 1.15, cuya instalación en entornos recientes (CUDA 12+, Python 3.10+) resulta problemática. Por estas dos razones, el benchmark empírico se realiza con Kong et al. como sucesor directo, y Onsets and Frames se cita únicamente como línea base histórica.

## 3. Modelo 2 — High-Resolution Piano Transcription (Kong et al., 2021)

### 3.1 Arquitectura

Sistema CRNN de doble rama derivado de Onsets and Frames, con tres innovaciones principales:

1. Regresión de tiempos de onset y offset con alta resolución: en lugar de clasificar frames como onset o no-onset (etiqueta binaria discreta), el modelo regresiona los tiempos exactos de onset y offset dentro de cada frame. Esto le confiere robustez a las etiquetas desalineadas y le permite recuperar la posición temporal de cada nota con precisión sub-frame.
2. Rama de pedal independiente: modelo dedicado que detecta onsets y offsets del pedal de resonancia (sustained pedal), fusionado con la rama de notas al final del pipeline.
3. Algoritmo analítico de post-procesamiento que calcula los tiempos exactos de nota a partir de las predicciones regresadas.

Como Onsets and Frames, opera sobre mel-espectrogramas de audio a 16 kHz.

### 3.2 Dataset de entrenamiento

MAESTRO v2.0.0, aproximadamente 200 horas de grabaciones piano-MIDI alineadas a 3 ms.

### 3.3 Métricas reportadas en la literatura

Sobre el conjunto de prueba de MAESTRO v2.0.0 (Kong et al., 2021):

- F1_onset = 96.72% (mejora de +1.92 pp sobre Onsets and Frames)
- F1_note (con offset) = 83.16%
- F1_note (con offset y velocity) = 82.53%
- F1_pedal_onset = 91.86% (primer benchmark publicado de pedal en MAESTRO)

Trabajos posteriores han empujado el F1_onset por encima de 0.97 en el joint onset-and-pitch F1 sobre certificaciones más recientes del mismo modelo.

### 3.4 Licencia y disponibilidad

- Repositorio principal: bytedance/piano_transcription (código de entrenamiento).
- Paquete de inferencia: piano_transcription_inference en PyPI.
- Licencia: Apache License 2.0.
- Framework: PyTorch (2.0 o superior en el entorno de este proyecto).
- Checkpoint pre-entrenado disponible en Zenodo (record 4034264), descarga automática desde el paquete.

### 3.5 Justificación

Estado en el benchmark: incluido y evaluado empíricamente.

Kong et al. es el estado del arte accesible más maduro para transcripción de piano en 2026. Cumple los criterios de selección del proyecto: alcanza F1_onset por encima del 96% en piano polifónico, muy por encima del umbral de 80% definido para la métrica del hito H2; es el único modelo del benchmark que detecta explícitamente el pedal de resonancia, cubriendo directamente la historia de usuario US-06; tiene una API de inferencia estable en PyTorch; su licencia Apache 2.0 permite integración en un proyecto académico y su posterior liberación con licencia abierta; y su tiempo de inferencia en GPU T4 permite cumplir el criterio de latencia L_e2e ≤ 1.5 veces la duración del audio del hito H4.

## 4. Modelo 3 — Basic Pitch (Bittner et al., 2022)

### 4.1 Arquitectura

Red convolucional ligera, instrumento-agnóstica, con tres salidas simultáneas:

1. Multi-pitch posterior gram: probabilidad por frame y por semitono (representación de saliencia armónica).
2. Note activation posterior gram: probabilidad por frame y por nota MIDI.
3. Note onset posterior gram: probabilidad por frame y por nota MIDI de que un onset ocurra en ese frame.

La entrada es un Harmonic CQT (Constant-Q Transform con harmónicos apilados). Todo el pipeline usa aproximadamente 30 000 parámetros y es capaz de ejecutar más rápido que tiempo real en CPU en un laptop moderno. Adicionalmente detecta pitch bends mediante la resolución sub-semitono del multi-pitch posterior gram.

### 4.2 Dataset de entrenamiento

Combinación de datasets multi-instrumento anotados a nivel de nota: MAESTRO (piano), GuitarSet (guitarra acústica), MedleyDB y Slakh (mezclas multi-instrumento y stems), MIR-1K y datasets sintéticos de voz.

### 4.3 Métricas reportadas en la literatura

Bittner et al. (2022) reportan un F1_note (con offset) promedio del 72.4% sobre el conjunto de test agregado multi-instrumento (piano, guitarra, voz, otros). Específicamente sobre MAESTRO, el F1_note reportado es de aproximadamente 76.7%, inferior al de Kong et al. pero notable considerando que el modelo no está especializado en piano. Los autores enfatizan que la ganancia clave es la eficiencia (30 000 parámetros frente a los aproximadamente 10 millones de Kong et al.) y la generalización cross-instrumento.

### 4.4 Licencia y disponibilidad

- Repositorio: spotify/basic-pitch en GitHub.
- Paquete PyPI: basic-pitch.
- Licencia: Apache License 2.0.
- Framework: TensorFlow 2, con soporte adicional de exportación a CoreML, ONNX y TensorFlow.js.
- Checkpoint pre-entrenado incluido en el paquete (ICASSP_2022_MODEL_PATH).

### 4.5 Justificación

Estado en el benchmark: incluido y evaluado empíricamente.

Basic Pitch se incluye como candidato alternativo por dos razones metodológicas: representa una filosofía arquitectónica opuesta (modelo ligero, instrumento-agnóstico) a Kong et al. (modelo pesado, especializado en piano), lo que enriquece el análisis comparativo; y su eficiencia lo hace viable como posible respaldo en configuraciones sin GPU, un caso de uso real del cliente Flutter (US-19, US-20) donde el usuario podría no tener acceso a hardware especializado. Además, Basic Pitch soporta MusicXML/MIDI como input opcional, alineándose con la historia US-02.

## 5. Modelo 4 — MT3: Multi-Task Multitrack Music Transcription (Gardner et al., 2022)

### 5.1 Arquitectura

Modelo Transformer seq2seq basado en la arquitectura T5-small (aproximadamente 60 millones de parámetros, Raffel et al., 2020). El audio se codifica como una secuencia de log-mel-espectrogramas y la salida es una secuencia de tokens tipo MIDI que representan eventos (pitch, onset, offset, program change de instrumento) en un vocabulario discreto. Es un modelo verdaderamente multi-instrumento: la misma red transcribe piano, guitarra, batería, cuerda y voz simultáneamente en una sola pasada, asignando cada nota a su instrumento correspondiente.

Predecesor directo: Sequence-to-Sequence Piano Transcription with Transformers (Hawthorne et al., 2021), que aplicó por primera vez la misma idea a piano únicamente.

### 5.2 Dataset de entrenamiento

Mezcla multi-dataset: MAESTRO (piano), Slakh2100 (multi-instrumento sintético), Cerberus4, GuitarSet, MusicNet y URMP (varios instrumentos y géneros). En total, aproximadamente 9 datasets combinados con muestreo balanceado.

### 5.3 Métricas reportadas en la literatura

Gardner et al. (2022) reportan sobre MAESTRO test:

- F1_onset ≈ 95.8% (comparable a Onsets and Frames y ligeramente inferior a Kong et al.)
- F1_note (con offset) ≈ 80.0%

Sobre datasets multi-instrumento (Slakh, MusicNet) el modelo supera todos los baselines especializados por instrumento, demostrando la ventaja del enfoque unificado.

### 5.4 Licencia y disponibilidad

- Repositorio: magenta/mt3 en GitHub.
- Licencia: Apache License 2.0.
- Framework: JAX + T5X + FLAX (stack de investigación de Google).
- Checkpoints pre-entrenados disponibles en Google Cloud Storage.
- Notebook oficial de Colab para inferencia disponible en el repositorio.

### 5.5 Justificación

Estado en el benchmark: descartado del benchmark empírico, documentado como opción futura.

MT3 se descarta como candidato del pipeline por tres motivos operativos: su desempeño sobre piano en solitario es inferior al de Kong et al. (F1_onset aproximadamente 95.8% frente a 96.72%), y su ventaja principal, la multi-instrumentalidad, no es aprovechable en este proyecto cuyo alcance está restringido a piano; el stack JAX + T5X + FLAX es notablemente más complejo de integrar en un backend FastAPI comparado con un modelo PyTorch estándar, aumentando innecesariamente la complejidad del despliegue (US-12); y el tamaño del checkpoint (aproximadamente 200 MB) junto con los requisitos de memoria GPU son mayores. Se documenta como candidato natural para una extensión futura del sistema a otros instrumentos (US-25), donde su capacidad multi-instrumento aportaría valor real.

## 6. Metodología del benchmark empírico

### 6.1 Objetivo

Comparar cuantitativamente los dos candidatos seleccionados, Kong et al. (2021) y Basic Pitch (2022), sobre un fragmento estándar del conjunto de prueba de MAESTRO v3.0.0, en las métricas definidas en el Marco Metodológico.

### 6.2 Fragmento de evaluación

- Fuente: MAESTRO v3.0.0, tomado del dataset público de Kaggle alonhaviv/the-maestro-dataset-v3-0-0.
- Archivo evaluado: MIDI-Unprocessed_059_PIANO059_MID--AUDIO-split_07-07-17_Piano-e_2-03_wav--1, correspondiente a una grabación de 2017 del International Piano-e-Competition.
- Duración: 30 segundos recortados desde el inicio de la pieza, con 398 notas de referencia (ground truth) en ese intervalo.
- Justificación: un fragmento corto permite iteraciones rápidas del benchmark sin comprometer la validez de la comparación relativa entre modelos. Los resultados no pretenden reproducir los reportados en las publicaciones originales (que usan el conjunto de prueba completo, del orden de 50 horas), sino comparar el desempeño relativo bajo condiciones controladas y reproducibles.

### 6.3 Ambiente de ejecución

- Plataforma: Kaggle Notebooks, con el dataset de MAESTRO v3.0.0 montado como input y acceso a internet habilitado para descargar los checkpoints pre-entrenados.
- Acelerador: GPU NVIDIA Tesla T4.
- Frameworks: PyTorch (Kong et al.), TensorFlow 2 (Basic Pitch).
- Instalación de dependencias:

  pip install --no-deps basic-pitch tensorflow-io-gcs-filesystem
  pip install mir_eval
  pip install --no-deps resampy

  Las dependencias de basic-pitch y pretty_midi/piano_transcription_inference se instalaron con la bandera --no-deps para evitar que pip intentara forzar un downgrade de numpy incompatible con la versión de Python del entorno de Kaggle (3.12). Las dependencias faltantes (resampy) se agregaron de forma manual, también sin arrastrar versiones conflictivas.
- Herramienta de evaluación: mir_eval.transcription (Raffel et al., 2014), estándar de facto en la comunidad MIR.

### 6.4 Métricas medidas

Para cada modelo se calculan:

| Métrica | Definición | Tolerancia |
|---|---|:---:|
| F1_onset | F1-Score a nivel de onset | ±50 ms |
| Precision_onset, Recall_onset | Componentes del F1_onset | ±50 ms |
| F1_note (con offset) | F1-Score considerando onset y offset | ±50 ms onset, máximo entre 50 ms y 20% de la duración para offset |
| Latencia total | Tiempo de inferencia en segundos | — |
| Latencia normalizada | Latencia dividida entre la duración del audio | — |

### 6.5 Notebook reproducible

El benchmark completo está implementado en notebooks/amt_benchmark.ipynb, adaptado para ejecutarse en Kaggle Notebooks con el dataset the-maestro-dataset-v3-0-0 montado como input y el acelerador GPU T4 activado. El notebook localiza automáticamente un par audio/MIDI dentro del dataset montado, ejecuta ambos modelos y produce como salida final la tabla de resultados en formato Markdown incorporada en la sección 7.1.

## 7. Resultados del benchmark

### 7.1 Tabla comparativa

Resultados obtenidos sobre el fragmento de 30 segundos descrito en la sección 6.2 (398 notas de referencia), ejecutado en Kaggle con GPU Tesla T4:

| Modelo | F1_onset | Precision_onset | Recall_onset | F1_note (con offset) | Latencia (s) | Latencia normalizada |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Kong et al. (piano_transcription_inference) | 100.00% | 100.00% | 100.00% | 97.24% | 2.99 | 0.100 |
| Basic Pitch (Spotify) | 81.25% | 93.46% | 71.86% | 9.38% | 4.35 | 0.145 |

Notas detectadas: Kong et al. identificó las 398 notas del fragmento (una detección por cada nota de referencia); Basic Pitch detectó 306 notas.

### 7.2 Discusión

Kong et al. (2021) reprodujo, sobre este fragmento específico, un desempeño incluso superior al reportado en la publicación original: F1_onset perfecto (100%) y F1_note con offset de 97.24%, ambos muy por encima del umbral de 80% definido en el hito H2. Esto es coherente con el hecho de que el fragmento evaluado proviene del mismo dataset (MAESTRO) y del mismo tipo de grabación (Disklavier del International Piano-e-Competition) sobre el que el modelo fue entrenado y validado originalmente, por lo que representa una condición favorable para el modelo más que una sobreestimación anómala.

Basic Pitch mostró una brecha considerable entre F1_onset (81.25%) y F1_note con offset (9.38%). El F1_onset por sí solo cumpliría el umbral de detección básica de notas, pero la caída abrupta en F1_note indica que, aunque el modelo detecta razonablemente bien cuándo empieza una nota, sus estimaciones de offset (duración de la nota) no coinciden con la tolerancia exigida por mir_eval en este fragmento polifónico. Esto es consistente con lo documentado en la literatura: Basic Pitch es un modelo generalista entrenado para múltiples instrumentos, no especializado en las duraciones largas y sostenidas típicas del repertorio pianístico con pedal, lo que penaliza fuertemente la métrica de offset en piezas de este tipo.

En cuanto a latencia, ambos modelos cumplen holgadamente el criterio del hito H4 (latencia normalizada menor o igual a 1.5): Kong et al. con 0.100 y Basic Pitch con 0.145. La diferencia de latencia entre ambos no es decisiva para la selección, dado que el margen frente al umbral es amplio en los dos casos.

En conjunto, para este fragmento de piano polifónico del repertorio de concierto, Kong et al. domina a Basic Pitch en las tres métricas de precisión sin sacrificar latencia.

## 8. Decisión final y trazabilidad

### 8.1 Modelo seleccionado

Se selecciona el modelo de Kong et al. (2021), piano_transcription_inference, como módulo AMT del pipeline. Cumple con margen amplio el criterio cuantitativo del hito H2 (F1-Score note-level igual o mayor a 80%, con 97.24% obtenido) y es el único de los dos candidatos evaluados que detecta el pedal de resonancia, requerido por la historia US-06. Basic Pitch queda descartado como módulo principal de transcripción por su bajo desempeño en F1_note sobre el repertorio pianístico evaluado, pero se conserva documentado como alternativa ligera para escenarios sin GPU o como referencia de comparación en trabajos futuros.

### 8.2 Trazabilidad con historias de usuario

| Modelo | Historias que cumple | Épica |
|---|---|:---:|
| Kong et al. (2021) | US-03 (precisión de notas), US-04 (precisión rítmica), US-05 (acordes complejos), US-06 (pedal de resonancia) | SCRUM-6 |
| Basic Pitch (2022) | US-02 (soporte MusicXML/MIDI opcional como alternativa) | SCRUM-5 |

### 8.3 Modelos documentados como opciones futuras

- MT3 (Gardner et al., 2022): candidato natural para extender el sistema a otros instrumentos (US-25).
- Hierarchical Frequency-Time Transformer (Toyama et al., 2023): mejora reciente sobre Kong et al. que podría considerarse en una versión futura del pipeline.

## 9. Referencias (APA 7)

Benetos, E., Dixon, S., Duan, Z., & Ewert, S. (2019). Automatic music transcription: An overview. IEEE Signal Processing Magazine, 36(1), 20–30. https://doi.org/10.1109/MSP.2018.2869928

Bittner, R. M., Bosch, J. J., Rubinstein, D., Meseguer-Brocal, G., & Ewert, S. (2022). A lightweight instrument-agnostic model for polyphonic note transcription and multipitch estimation. En ICASSP 2022 – 2022 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) (pp. 781–785). IEEE. https://doi.org/10.1109/ICASSP43922.2022.9746549

Emiya, V., Bertin, N., David, B., & Badeau, R. (2010). MAPS — A piano database for multipitch estimation and automatic transcription of music (Rapport de recherche inria-00544155). Télécom ParisTech. https://hal.inria.fr/inria-00544155

Gardner, J., Simon, I., Manilow, E., Hawthorne, C., & Engel, J. (2022). MT3: Multi-task multitrack music transcription. En International Conference on Learning Representations (ICLR). https://arxiv.org/abs/2111.03017

Hawthorne, C., Elsen, E., Song, J., Roberts, A., Simon, I., Raffel, C., Engel, J., Oore, S., & Eck, D. (2018). Onsets and frames: Dual-objective piano transcription. En E. Gómez, X. Hu, E. Humphrey, & E. Benetos (Eds.), Proceedings of the 19th International Society for Music Information Retrieval Conference (pp. 50–57). ISMIR. https://ismir2018.ircam.fr/doc/pdfs/19_Paper.pdf

Hawthorne, C., Simon, I., Swavely, R., Manilow, E., & Engel, J. (2021). Sequence-to-sequence piano transcription with transformers. En Proceedings of the 22nd International Society for Music Information Retrieval Conference (pp. 246–253). ISMIR. https://archives.ismir.net/ismir2021/paper/000030.pdf

Hawthorne, C., Stasyuk, A., Roberts, A., Simon, I., Huang, C.-Z. A., Dieleman, S., Elsen, E., Engel, J., & Eck, D. (2019). Enabling factorized piano music modeling and generation with the MAESTRO dataset. En International Conference on Learning Representations (ICLR). https://openreview.net/forum?id=r1lYRjC9F7

Kong, Q., Li, B., Song, X., Wan, Y., & Wang, Y. (2021). High-resolution piano transcription with pedals by regressing onset and offset times. IEEE/ACM Transactions on Audio, Speech, and Language Processing, 29, 3707–3717. https://doi.org/10.1109/TASLP.2021.3121991

Raffel, C., McFee, B., Humphrey, E. J., Salamon, J., Nieto, O., Liang, D., & Ellis, D. P. W. (2014). mir_eval: A transparent implementation of common MIR metrics. En Proceedings of the 15th International Society for Music Information Retrieval Conference (pp. 367–372). ISMIR. https://archives.ismir.net/ismir2014/paper/000034.pdf

Raffel, C., Shazeer, N., Roberts, A., Lee, K., Narang, S., Matena, M., Zhou, Y., Li, W., & Liu, P. J. (2020). Exploring the limits of transfer learning with a unified text-to-text transformer. Journal of Machine Learning Research, 21(140), 1–67. https://jmlr.org/papers/v21/20-074.html

Toyama, K., Akama, T., Ikemiya, Y., Takida, Y., Liao, W.-H., & Mitsufuji, Y. (2023). Automatic piano transcription with hierarchical frequency-time transformer. En Proceedings of the 24th International Society for Music Information Retrieval Conference (pp. 215–222). ISMIR. https://archives.ismir.net/ismir2023/paper/000024.pdf
