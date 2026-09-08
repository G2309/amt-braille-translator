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
3. Transformer, en dos variantes: la seq2seq con vocabulario tipo MIDI y arquitectura T5, representada por Sequence-to-Sequence Piano Transcription (Hawthorne et al., 2021) y su extensión multi-instrumento MT3 (Gardner et al., 2022); y la jerárquica frecuencia-tiempo del hFT-Transformer (Toyama et al., 2023).

Este documento caracteriza cinco modelos de esas tres familias. Tres de ellos se evalúan empíricamente sobre obras completas (Kong et al., Basic Pitch y hFT-Transformer); Onsets and Frames se conserva como línea base bibliográfica y MT3 se descarta por motivos operativos, ambos con la justificación detallada en su sección correspondiente.

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

## 6. Modelo 5 — hFT-Transformer (Toyama et al., 2023)

### 6.1 Arquitectura

Transformer jerárquico de dos niveles sobre el eje frecuencia-tiempo. El primer nivel combina un bloque convolucional en el eje temporal, un codificador Transformer en el eje de frecuencia y un decodificador; el segundo aplica otro codificador Transformer sobre el eje temporal. Opera sobre mel-espectrogramas de 256 bandas a 16 kHz y produce cuatro salidas por nivel: onset, offset, actividad (mpe) y velocidad, para las 88 notas del piano.

### 6.2 Dataset de entrenamiento

MAESTRO v3.0.0. El checkpoint publicado (`model_016_003.pkl`, release ISMIR 2023) corresponde al modelo entrenado sobre la partición de entrenamiento de ese conjunto.

### 6.3 Licencia y disponibilidad

- Repositorio: `sony/hFT-Transformer` en GitHub, licencia MIT.
- Framework: PyTorch, con `torchaudio` para el cálculo de la característica de entrada.
- Checkpoint: se descarga del release `ismir2023`.

A diferencia de Kong et al., no se distribuye como paquete instalable: hay que clonar el repositorio, y el archivo de configuración que consume el modelo no es el que viene publicado sino uno derivado, al que `corpus/make_dataset.py` agrega los campos `min_value`, `max_value` y `n_bins`. Sin ellos la inferencia falla. El notebook del benchmark reconstruye ese config.

### 6.4 Justificación

Estado en el benchmark: incluido y evaluado empíricamente.

Se incorporó como tercera familia arquitectónica del benchmark, en sustitución de Onsets and Frames, que no pudo evaluarse empíricamente por depender de TensorFlow 1.15 (ver sección 2.5) y para el que no existe un checkpoint público utilizable en el entorno de ejecución. Con hFT-Transformer las tres familias del estado del arte quedan representadas por modelos ejecutables: la CRNN de doble objetivo en su variante de alta resolución (Kong et al.), la CNN ligera instrumento-agnóstica (Basic Pitch) y el Transformer jerárquico (hFT).

## 7. Metodología del benchmark empírico

### 7.1 Objetivo

Comparar cuantitativamente tres arquitecturas sobre **obras completas** de la partición de prueba de MAESTRO v3.0.0, para verificar los umbrales del primer objetivo específico: F1 de onset ≥ 80 %, F1 a nivel de nota ≥ 75 % y Tasa de Error de Nota ≤ 25 %.

### 7.2 Conjunto de evaluación

Veinte obras completas tomadas de las 177 de la partición de prueba, seleccionadas por muestreo aleatorio con semilla fija (22779) para no sesgar por compositor ni por duración. Suman unas 2.4 horas de audio y abarcan desde Scarlatti hasta Debussy. La partición de prueba está excluida del entrenamiento de los tres modelos. La lista exacta queda registrada en `benchmark_full_por_obra.csv`.

### 7.3 Convención de evaluación de los offsets

Esta es la decisión metodológica que más afecta al resultado y conviene explicitarla.

La referencia de MAESTRO registra el instante en que se suelta la tecla. Sin embargo, los modelos entrenados sobre ese corpus aprenden offsets **prolongados por el pedal de resonancia**: mientras el pedal está pisado la nota sigue sonando, y esa es la convención con la que la línea Onsets and Frames y Kong et al. reportan sus métricas. Comparar contra los offsets crudos penaliza al modelo por acertar.

El efecto es cuantitativamente decisivo. Una primera corrida contra los offsets sin extender dio para Kong et al. un F1 a nivel de nota de **33.38 % con desviación estándar de ±26.56**, con el repertorio de pedal denso hundido (Rachmaninoff 3 %, Chopin 10 %) y el barroco intacto (Scarlatti 78 %). Repetida la medición extendiendo cada offset de la referencia mientras el control 64 permanece por encima de 64 —y recortándolo en el siguiente ataque de la misma altura—, el mismo modelo sobre las mismas obras pasa a **83.74 % ± 4.87**, prácticamente el 83.16 % que reportan sus autores.

El hallazgo es relevante más allá de este proyecto: la elección de la convención de offset mueve la métrica más de cincuenta puntos porcentuales, y ninguna de las dos alternativas es incorrecta en abstracto. Refuerza el argumento sobre el vacío de medición que motiva la Tasa de Exactitud de Símbolo Braille.

### 7.4 Métricas medidas

| Métrica | Definición | Tolerancia |
|---|---|:---:|
| F1_onset | F1 a nivel de onset con altura correcta | ±50 ms |
| F1_note | F1 considerando onset y offset | ±50 ms onset; offset dentro de max(50 ms, 20 % de la duración) |
| NER | (omisiones + inserciones) / notas de referencia, sobre el emparejamiento onset-altura | ±50 ms |
| Latencia normalizada | tiempo de inferencia entre duración del audio | — |

Calculadas con `mir_eval.transcription` (Raffel et al., 2014).

### 7.5 Ambiente y reproducibilidad

Kaggle Notebooks con GPU Tesla T4, dataset `alonhaviv/the-maestro-dataset-v3-0-0` montado como input. El notebook `notebooks/amt-benchmark-full.ipynb` es reanudable y guarda las notas estimadas crudas junto a las métricas, de modo que un cambio en la convención de evaluación puede recalcularse sin volver a ejecutar la inferencia. La corrida completa de los tres modelos sobre las veinte obras tomó 34 minutos.

## 8. Resultados del benchmark

### 8.1 Tabla comparativa

Sesenta transcripciones (tres modelos × veinte obras), sin fallos:

| Modelo | Obras | F1_onset | F1_note (con offset) | NER | Latencia norm. (media / p90) |
|---|:---:|:---:|:---:|:---:|:---:|
| Kong et al. (2021) | 20 | 95.89 % ± 2.82 % | 83.74 % ± 4.87 % | 8.01 % | 0.097 / 0.098 |
| hFT-Transformer (2023) | 20 | 96.68 % ± 2.44 % | 89.30 % ± 4.35 % | 6.36 % | 0.079 / 0.081 |
| Basic Pitch (2022) | 20 | 64.75 % ± 8.21 % | 19.46 % ± 6.71 % | 63.37 % | 0.030 / 0.043 |
| Onsets and Frames (2018), línea base bibliográfica | — | 94.80 % (publicado) | 82.60 % (publicado) | — | — |

Verificación de umbrales del hito H2: **Kong et al. y hFT-Transformer cumplen los tres**; Basic Pitch no cumple ninguno.

### 8.2 Discusión

**Kong et al.** reproduce sobre obras completas los valores de su publicación, lo que valida el montaje experimental. Su dispersión por obra es baja y el rango va de 74.3 % (Rachmaninoff, *Étude-Tableaux* Op. 39 No. 5) a 91.3 % (Scarlatti), un gradiente coherente con la densidad armónica y el uso de pedal del repertorio.

**hFT-Transformer** supera a Kong et al. en las tres métricas de precisión y además es más rápido, con la ventaja mayor en el F1 a nivel de nota (+5.56 puntos), que es donde pesa la estimación del offset: es justamente lo que cabría esperar de una arquitectura que modela explícitamente la dimensión temporal con un codificador dedicado. Su obra peor evaluada (81.4 %) queda por encima del umbral exigido.

**Basic Pitch** confirma lo documentado en la literatura. Su F1 de onset del 64.75 % ya queda lejos del umbral, y el desplome del F1 a nivel de nota refleja que un modelo generalista entrenado sobre múltiples instrumentos no modela bien las duraciones largas y sostenidas del repertorio pianístico con pedal. Queda descartado como módulo principal.

En latencia los tres cumplen con holgura el criterio del hito H4: la etapa acústica consume menos de la décima parte de la duración del audio, lo que deja un margen amplio para el resto del pipeline.

## 9. Decisión final y trazabilidad

### 9.1 Modelo seleccionado

Se selecciona **Kong et al. (2021)** como módulo acústico del sistema, pese a que hFT-Transformer obtiene mejores métricas de nota. La decisión se apoya en tres razones.

La primera es funcional: **hFT-Transformer no detecta el pedal de resonancia**. Su salida son las 88 notas del piano y nada más, mientras que Kong et al. incorpora una rama dedicada al pedal, que es el primer benchmark publicado de esa tarea sobre MAESTRO y que cubre la historia US-06.

La segunda es arquitectónica: la ventaja de hFT se concentra en la precisión del offset, y esa precisión **la absorbe el cuantizador rítmico**. Como el módulo determinista ajusta las duraciones a una grilla de semicorchea antes de asignar figuras, una diferencia de pocos milisegundos en el offset no cambia la figura que termina escrita en el archivo BRF. La ganancia medida no se propaga hasta la salida del sistema.

La tercera es operativa: Kong et al. se instala como paquete de PyPI con descarga automática del checkpoint, mientras que hFT-Transformer exige clonar el repositorio, reconstruir su archivo de configuración y cargar el modelo desde un pickle. Esa fricción recae sobre el backend del cuarto objetivo específico.

La diferencia entre ambos queda documentada y medida, de modo que la elección es una decisión de ingeniería justificada sobre evidencia propia y no una suposición heredada de la literatura.

### 9.2 Trazabilidad con historias de usuario

| Modelo | Historias que cumple | Épica |
|---|---|:---:|
| Kong et al. (2021) | US-03 (precisión de notas), US-04 (precisión rítmica), US-05 (acordes complejos), US-06 (pedal de resonancia) | SCRUM-6 |
| Basic Pitch (2022) | US-02 (soporte MusicXML/MIDI opcional como alternativa) | SCRUM-5 |

### 9.3 Modelos documentados como opciones futuras

- **hFT-Transformer (Toyama et al., 2023)**: la mejora inmediata del sistema si se resuelve la detección de pedal, ya sea combinándolo con la rama de pedal de Kong et al. o prescindiendo de ella. Ventaja medida: +5.56 puntos de F1 a nivel de nota y menor latencia.
- **MT3 (Gardner et al., 2022)**: candidato natural para extender el sistema a otros instrumentos (US-25).

## 10. Referencias (APA 7)

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
