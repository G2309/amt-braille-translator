# Revisión de Literatura — Modelos de Transcripción Musical Automática (AMT) Polifónica

Este documento resume el estado del arte de los modelos de Transcripción Musical Automática (AMT) polifónica considerados como candidatos para el módulo de inferencia AMT del sistema. Cada modelo se caracteriza por su arquitectura, dataset de entrenamiento, métricas reportadas en la literatura, licencia y justificación de inclusión o descarte del benchmark comparativo (Fase 2 del Marco Metodológico).

La revisión sigue la nomenclatura métrica del Marco Metodológico:

- **F1_onset:** F1-Score a nivel de onset, considerando una nota correcta si el modelo predice el inicio con una tolerancia de ±50 ms respecto al ground truth.
- **F1_note:** F1-Score a nivel de nota con offset, considerando correcta una nota solo si onset y offset están dentro de tolerancia (típicamente ±50 ms para onset y el máximo entre 50 ms o el 20 % de la duración para offset).
- **NER (Note Error Rate):** tasa de error a nivel de nota, complementaria del F1_note.

---

## 1. Contexto histórico y taxonomía

La AMT polifónica busca convertir una señal de audio en una representación simbólica que preserve las notas, sus onsets, offsets, alturas tonales y (opcionalmente) velocidades e información de pedal. Durante casi dos décadas dominaron los enfoques basados en factorización de matrices no negativas (NMF) y máquinas de estados ocultos, con desempeño limitado por su incapacidad de modelar dependencias temporales largas y estructuras armónicas complejas (Benetos et al., 2019).

A partir de 2017 la investigación se orientó de forma casi total al aprendizaje profundo, con tres familias arquitectónicas dominantes:

1. **CNN + BiLSTM** con doble objetivo onset/frame — inaugurada por *Onsets and Frames* (Hawthorne et al., 2018) y refinada por Kong et al. (2021).
2. **CNN ligera multi-tarea** — representada por *Basic Pitch* (Bittner et al., 2022), enfocada en instrumento-agnosticismo y eficiencia computacional.
3. **Transformer seq2seq** — representada por *Sequence-to-Sequence Piano Transcription* (Hawthorne et al., 2021) y su extensión multi-instrumento *MT3* (Gardner et al., 2022), con vocabulario tipo MIDI y arquitectura T5.

Estos cuatro modelos constituyen los candidatos evaluados en este documento.

---

## 2. Modelo 1 — Onsets and Frames (Hawthorne et al., 2018)

### 2.1 Arquitectura

Red neuronal profunda compuesta por dos ramas paralelas:

- **Onset stack:** CNN (3 capas convolucionales) → BiLSTM → capa densa que predice, por cada frame, la probabilidad de que un onset comience en ese frame para cada una de las 88 notas del piano.
- **Frame stack:** CNN → BiLSTM → capa densa que predice la actividad de cada nota en cada frame.

La rama de frames se condiciona con la salida de la rama de onsets (concatenación de features intermedios). En inferencia, la actividad de frames se filtra con la predicción de onsets: una nota nueva solo se activa si la rama de onsets también predice un onset para ese frame. Adicionalmente, el modelo predice velocidades normalizadas por nota.

La entrada del modelo es un mel-espectrograma logarítmico calculado sobre audio a 16 kHz.

### 2.2 Dataset de entrenamiento

- **MAPS** (Emiya et al., 2010): base de datos de piano sintético y grabaciones reales de un Disklavier con MIDI alineado.
- **MAESTRO v1.0.0** (Hawthorne et al., 2019): ~172 horas de grabaciones del *International Piano-e-Competition* con MIDI alineado a nivel de milisegundos por medio de un Disklavier Yamaha.

### 2.3 Métricas reportadas en la literatura

Sobre el conjunto de prueba de MAESTRO v1.0.0 (Hawthorne et al., 2019):

- F1_onset ≈ 94.80 % (Hawthorne et al., 2018).
- F1_note (con offset) ≈ 82.60 %.
- F1_frame ≈ 90.20 %.

### 2.4 Licencia y disponibilidad

- Código original: Apache License 2.0 (repositorio *magenta/magenta* en GitHub).
- Framework: TensorFlow 1.15.
- Existen implementaciones de terceros en PyTorch (p. ej. *jongwook/onsets-and-frames*, MIT License) con checkpoints entrenados sobre MAESTRO.

### 2.5 Justificación

**Estado en el benchmark: incluido como baseline histórico, no evaluado empíricamente.**

*Racional:* Onsets and Frames marcó el punto de inflexión de la AMT polifónica moderna, pero su desempeño ha sido superado por Kong et al. (2021), quienes emplean la misma arquitectura CRNN mejorada con regresión de onsets/offsets de alta resolución sobre el mismo dataset. Los autores de Kong et al. reportan directamente el F1_onset de Onsets and Frames como línea base (94.80 %) y muestran una mejora absoluta de casi 2 puntos porcentuales. Adicionalmente, el código original de Onsets and Frames depende de TensorFlow 1.15, cuya instalación en entornos recientes (CUDA 12+, Python 3.10+) resulta problemática. Por estas dos razones, el benchmark empírico se realiza con Kong et al. como sucesor directo, y Onsets and Frames se cita únicamente como línea base histórica.

---

## 3. Modelo 2 — High-Resolution Piano Transcription (Kong et al., 2021)

### 3.1 Arquitectura

Sistema CRNN de doble rama derivado de Onsets and Frames, con tres innovaciones principales:

1. **Regresión de tiempos de onset y offset con alta resolución:** en lugar de clasificar frames como onset/no-onset (etiqueta binaria discreta), el modelo regresiona los tiempos exactos de onset y offset dentro de cada frame. Esto le confiere robustez a las etiquetas desalineadas y le permite recuperar la posición temporal de cada nota con precisión sub-frame.
2. **Rama de pedal independiente:** modelo dedicado que detecta onsets y offsets del pedal de resonancia (sustained pedal), fusionado con la rama de notas al final del pipeline.
3. **Algoritmo analítico de post-procesamiento** que calcula los tiempos exactos de nota a partir de las predicciones regresadas.

Como Onsets and Frames, opera sobre mel-espectrogramas de audio a 16 kHz.

### 3.2 Dataset de entrenamiento

- **MAESTRO v2.0.0** (~200 horas de grabaciones piano-MIDI alineadas a 3 ms).

### 3.3 Métricas reportadas en la literatura

Sobre el conjunto de prueba de MAESTRO v2.0.0 (Kong et al., 2021):

- F1_onset = **96.72 %** (mejora de +1.92 pp sobre Onsets and Frames).
- F1_note (con offset) = **83.16 %**.
- F1_note (con offset + velocity) = **82.53 %**.
- F1_pedal_onset = **91.86 %** (primer benchmark publicado de pedal en MAESTRO).

Trabajos posteriores han empujado el F1_onset por encima de 0.97 en el joint onset-and-pitch F1 (Kong et al. 2021 en la evaluación certificada, 2026).

### 3.4 Licencia y disponibilidad

- Repositorio principal: *bytedance/piano_transcription* (código de entrenamiento).
- Paquete de inferencia: *piano_transcription_inference* en PyPI (`pip install piano_transcription_inference`).
- Licencia: Apache License 2.0.
- Framework: PyTorch (≥ 1.4).
- Checkpoint pre-entrenado disponible en Zenodo (record 4034264), descarga automática desde el paquete.

### 3.5 Justificación

**Estado en el benchmark: incluido y evaluado empíricamente.**

*Racional:* Kong et al. es el estado del arte accesible más maduro para transcripción de piano en 2026. Cumple los cinco criterios de selección del proyecto: (a) alcanza F1_onset ≥ 96 % en piano polifónico, muy por encima del umbral de 80 % definido para la métrica del hito H2; (b) es el único modelo del benchmark que detecta explícitamente el pedal de resonancia, cubriendo directamente la historia de usuario US-06; (c) tiene una API de inferencia estable en PyTorch; (d) su licencia Apache 2.0 permite integración en un proyecto académico y su posterior liberación con licencia abierta; (e) su tiempo de inferencia en GPU T4 (Colab gratuito) permite cumplir el criterio de latencia L_e2e ≤ 1.5× duración del audio del hito H4.

---

## 4. Modelo 3 — Basic Pitch (Bittner et al., 2022)

### 4.1 Arquitectura

Red convolucional ligera, instrumento-agnóstica, con tres salidas simultáneas:

1. **Multi-pitch posterior gram:** probabilidad por frame y por semitono (representación de saliencia armónica).
2. **Note activation posterior gram:** probabilidad por frame y por nota MIDI.
3. **Note onset posterior gram:** probabilidad por frame y por nota MIDI de que un onset ocurra en ese frame.

La entrada es un *Harmonic CQT* (Constant-Q Transform con harmónicos apilados). Todo el pipeline usa ~30 000 parámetros y es capaz de ejecutar más rápido que tiempo real en CPU en un laptop moderno. Adicionalmente detecta *pitch bends* mediante la resolución sub-semitono del multi-pitch posterior gram.

### 4.2 Dataset de entrenamiento

Combinación de datasets multi-instrumento anotados a nivel de nota:

- **MAESTRO** (piano).
- **GuitarSet** (guitarra acústica).
- **MedleyDB** y **Slakh** (mezclas multi-instrumento y stems).
- **MIR-1K** y datasets sintéticos de voz.

### 4.3 Métricas reportadas en la literatura

Bittner et al. (2022) reportan un F1_note (con offset) promedio del **72.4 %** sobre el conjunto de test agregado multi-instrumento (piano, guitarra, voz, otros). Específicamente sobre MAESTRO, el F1_note reportado es de **~76.7 %**, inferior al de Kong et al. pero notable considerando que el modelo no está especializado en piano. Los autores enfatizan que la ganancia clave es la **eficiencia** (30 000 parámetros vs. ~10 M en Kong et al.) y la **generalización cross-instrumento**.

### 4.4 Licencia y disponibilidad

- Repositorio: *spotify/basic-pitch* en GitHub.
- Paquete PyPI: `pip install basic-pitch`.
- Licencia: Apache License 2.0.
- Framework: TensorFlow 2 + CoreML (soporta también export a ONNX y TensorFlow.js).
- Checkpoint pre-entrenado incluido en el paquete (ICASSP_2022_MODEL_PATH).

### 4.5 Justificación

**Estado en el benchmark: incluido y evaluado empíricamente.**

*Racional:* Basic Pitch se incluye como candidato alternativo por dos razones metodológicas: (a) representa una filosofía arquitectónica opuesta (modelo ligero, instrumento-agnóstico) a Kong et al. (modelo pesado, especializado en piano), lo que enriquece el análisis comparativo; (b) su eficiencia lo hace viable como fallback en configuraciones sin GPU, cubriendo un caso de uso real del cliente Flutter (US-19, US-20) donde el usuario podría no tener acceso a hardware especializado. Además, Basic Pitch soporta MusicXML/MIDI como input opcional, alineándose con la historia US-02.

---

## 5. Modelo 4 — MT3: Multi-Task Multitrack Music Transcription (Gardner et al., 2022)

### 5.1 Arquitectura

Modelo Transformer seq2seq basado en la arquitectura **T5-small** (~60 M parámetros, Raffel et al., 2020). El audio se codifica como una secuencia de log-mel-espectrogramas y la salida es una secuencia de tokens tipo MIDI que representan eventos (pitch, onset, offset, program change de instrumento) en un vocabulario discreto. Es un modelo verdaderamente multi-instrumento: la misma red transcribe piano, guitarra, batería, cuerda y voz simultáneamente en una sola pasada, asignando cada nota a su instrumento correspondiente.

Predecesor directo: *Sequence-to-Sequence Piano Transcription with Transformers* (Hawthorne et al., 2021), que aplicó por primera vez la misma idea a piano únicamente.

### 5.2 Dataset de entrenamiento

Mezcla multi-dataset:

- **MAESTRO** (piano).
- **Slakh2100** (multi-instrumento sintético).
- **Cerberus4**, **GuitarSet**, **MusicNet**, **URMP** (varios instrumentos y géneros).

Total: ~9 datasets combinados con muestreo balanceado.

### 5.3 Métricas reportadas en la literatura

Gardner et al. (2022) reportan sobre MAESTRO test:

- F1_onset ≈ **95.8 %** (comparable a Onsets and Frames y ligeramente inferior a Kong et al.).
- F1_note (con offset) ≈ **80.0 %**.

Sobre datasets multi-instrumento (Slakh, MusicNet) el modelo supera todos los baselines especializados por instrumento, demostrando la ventaja del enfoque unificado.

### 5.4 Licencia y disponibilidad

- Repositorio: *magenta/mt3* en GitHub.
- Licencia: Apache License 2.0.
- Framework: JAX + T5X + FLAX (stack de investigación de Google).
- Checkpoints pre-entrenados disponibles en Google Cloud Storage.
- Notebook oficial de Colab para inferencia disponible en el repositorio.

### 5.5 Justificación

**Estado en el benchmark: descartado del benchmark empírico; documentado como opción futura.**

*Racional:* MT3 se descarta como candidato del pipeline por tres motivos operativos: (a) su desempeño sobre piano en solitario es **inferior** al de Kong et al. (F1_onset ~95.8 % vs. 96.72 %), y su ventaja principal — la multi-instrumentalidad — no es aprovechable en este proyecto cuyo alcance está restringido a piano; (b) el stack JAX + T5X + FLAX es notablemente más complejo de integrar en un backend FastAPI comparado con un modelo PyTorch estándar, aumentando innecesariamente la complejidad del despliegue (US-12); (c) el tamaño del checkpoint (~200 MB) y los requisitos de memoria GPU son mayores. Se documenta como candidato natural para una extensión futura del sistema a otros instrumentos (US-25), donde su capacidad multi-instrumento aportaría valor real.

---

## 6. Metodología del benchmark empírico

### 6.1 Objetivo

Comparar cuantitativamente los dos candidatos seleccionados — Kong et al. (2021) y Basic Pitch (2022) — sobre un fragmento estándar del conjunto de prueba de MAESTRO v3.0.0, en las métricas definidas en el Marco Metodológico.

### 6.2 Fragmento de evaluación

- **Fuente:** conjunto de prueba (test split) de MAESTRO v3.0.0 (Hawthorne et al., 2019).
- **Duración:** 30 segundos recortados desde el inicio de una pieza polifónica del test set.
- **Justificación:** un fragmento corto permite iteraciones rápidas del benchmark en Google Colab (GPU T4 gratuita) sin comprometer la validez de la comparación relativa entre modelos. Los resultados no pretenden reproducir los reportados en las publicaciones originales (que usan el test set completo, ~50 horas), sino comparar el desempeño relativo bajo condiciones controladas y reproducibles.

### 6.3 Ambiente de ejecución

- **Plataforma:** Google Colab con GPU NVIDIA T4 (16 GB VRAM).
- **Frameworks:** PyTorch 2.x + CUDA 12.x (Kong et al.), TensorFlow 2.x (Basic Pitch).
- **Herramienta de evaluación:** `mir_eval.transcription` (Raffel et al., 2014), estándar de facto en la comunidad MIR.

### 6.4 Métricas medidas

Para cada modelo se calculan:

| Métrica | Definición | Tolerancia |
|:---|:---|:---:|
| F1_onset | F1-Score a nivel de onset | ±50 ms |
| Precision_onset, Recall_onset | Componentes del F1_onset | ±50 ms |
| F1_note (con offset) | F1-Score considerando onset + offset | ±50 ms onset, max(50 ms, 20 % dur) offset |
| Latencia total | Tiempo de inferencia en segundos | — |
| Latencia normalizada | Latencia / duración del audio | — |

### 6.5 Notebook reproducible

El benchmark completo está implementado en `notebooks/amt_benchmark.ipynb`. El notebook se ejecuta en Colab con un solo click ("Run all") y produce como salida final la tabla de resultados en formato Markdown lista para incorporar a esta revisión de literatura.

---

