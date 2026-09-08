# Subset de Reglas de Musicografía Braille — Alcance del Módulo de Traducción

Este documento define el subconjunto de **veintiocho reglas**, distribuidas en **nueve secciones**, del Manual Simplificado de Musicografía Braille (Aller Pérez, ONCE, 2001) que implementa el módulo determinista de traducción (FSM + AST + renderizador Bar-over-bar) del sistema.

Las reglas se identifican por su **numeración original del Manual** (formato X-Y, donde X es el capítulo en numeración romana del índice y Y el número correlativo de la regla dentro del capítulo). Los signos que el Manual presenta en tablas sin número de regla se citan por su tabla (p. ej. «Tabla 9 A»). Esta numeración fue verificada contra el PDF del Manual el 20-08-2026; los glifos de las Tablas 1, 5, 6, 9 A y del Ejemplo 1-9 se cotejaron visualmente.

Referencia bibliográfica: Aller Pérez, J. (2001). *Manual Simplificado de Musicografía Braille — Versión para usuarios no ciegos*. Madrid: Organización Nacional de Ciegos Españoles (ONCE). ISBN: 84-484-0240-5.

## Convenciones de notación en este documento

Para representar los símbolos Braille en texto plano se emplean tres notaciones complementarias:

* Puntos del cajetín Braille: los seis puntos del cajetín se enumeran de arriba abajo y de izquierda a derecha como 1-2-3 (columna izquierda) y 4-5-6 (columna derecha). Por ejemplo, la letra d en Braille literario ocupa los puntos 1-4-5.
* Unicode Braille: el carácter del rango U+2800–U+28FF (ej: ⠙ para los puntos 1-4-5).
* Descripción textual: para reglas condicionales complejas se acompaña la descripción en prosa.

## Alcance implementado en el sistema

Las nueve secciones del subset, en orden de prioridad para el cálculo del BSA:

| # | Sección del subset | Capítulo del Manual | Reglas |
| --- | --- | --- | --- |
| 1 | Notas, figuras y silencios | I.A | 1-1, 1-2, 1-3, 1-6 |
| 2 | Signos de octava | I.B | 1-9, 1-10 |
| 3 | Alteraciones, armadura y compás | III | 3-1, 3-3, 3-6, 3-8 |
| 4 | Intervalos armónicos | V.A | 5-1, 5-2, 5-5, 5-6 |
| 5 | In-accords (cópulas) | V.B | 5-10, 5-11, 5-12, 5-14 |
| 6 | Ligaduras | VI | 6-2, 6-3, 6-9 |
| 7 | Barras de compás | IX.A | 9-1 (+ Tabla 9 A) |
| 8 | Bar-over-bar (compás sobre compás) | XIV.C.1 | 14-16, 14-17, 14-18, 14-22 |
| 9 | Signos de mano para piano | XV | 15-2, 15-3 |

Total: 4+2+4+4+4+3+1+4+2 = **28 reglas**.

Las secciones del Manual fuera de alcance para la versión inicial (documentadas al final para trazabilidad) son: claves (II), grupos rítmicos con signos de agrupación (IV), signos de doble figura (V.C), trémolos (VII), digitación (VIII), repeticiones (IX.B/IX.C), matices (X), adornos (XI), teoría y bajo cifrado (XII), notación moderna (XIII), pedal de piano en su notación Braille específica (XV, reglas 15-11 a 15-22) y todo lo referente a instrumentos distintos del piano (XVI en adelante).

---

## 1. Notas, figuras y silencios (Sección I.A, Tabla 1)

### Regla 1-1 — Codificación de notas y figuras

Las siete notas Do, Re, Mi, Fa, Sol, La, Si se codifican con las letras Braille d, e, f, g, h, i, j respectivamente (combinaciones de los puntos 1, 2, 4 y 5). Los puntos 3 y 6, dentro de la misma celdilla, determinan la figura. Cada símbolo representa dos valores rítmicos que se distinguen por contexto.

Tabla completa, verificada contra la Tabla 1 del Manual:

| Grupo (puntos añadidos) | Do | Re | Mi | Fa | Sol | La | Si | Silencio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Redondas y semicorcheas (3 y 6) | ⠽ | ⠵ | ⠯ | ⠿ | ⠷ | ⠮ | ⠾ | ⠍ |
| Blancas y fusas (3) | ⠝ | ⠕ | ⠏ | ⠟ | ⠗ | ⠎ | ⠞ | ⠥ |
| Negras y semifusas (6) | ⠹ | ⠱ | ⠫ | ⠻ | ⠳ | ⠪ | ⠺ | ⠧ |
| Corcheas y garrapateas (ninguno) | ⠙ | ⠑ | ⠋ | ⠛ | ⠓ | ⠊ | ⠚ | ⠭ |

Implementación: `braille_tables.note_cell` construye la celda como letra base + puntos de duración, y `braille_tables.REST` contiene los silencios.

### Regla 1-2 — Puntillo

El puntillo se representa con el punto 3 (⠄) colocado inmediatamente después de la nota o silencio afectado, sin ningún signo intercalado. El doble puntillo añade otro punto 3.

### Regla 1-3 — Signos de valor mayor, valor menor y separación de valores

Cuando el contexto no basta para determinar si un símbolo representa el valor mayor o el menor de su par, el Manual define tres signos. Verificados contra la Tabla 1:

| Signo | Puntos | Unicode |
| --- | --- | --- |
| Valores mayores (redonda, blanca, negra, corchea) | 4-5, 1-2-6, 2 | ⠘⠣⠂ |
| Valores menores (semicorchea, fusa, semifusa, garrapatea) | 6, 1-2-6, 2 | ⠠⠣⠂ |
| Separación de valores | 5-6, 1-3 | ⠰⠅ |

El sistema todavía no emite estos signos: el cuantizador produce una grilla de semicorchea donde el número de eventos por compás desambigua el valor. Quedan documentados como mejora pendiente para pasajes con mezcla de valores extremos (caso de la regla 1-5).

### Regla 1-6 — Compás de espera (silencio prolongado)

Para representar compases completos de silencio se usa siempre el silencio de redonda:

* 2 o 3 compases consecutivos: repetición del silencio de redonda.
* 4 o más compases consecutivos: signo numérico + número de compases + silencio de redonda.

El cuantizador rellena con silencio de redonda cada compás vacío (forma expandida; la forma abreviada con número queda pendiente).

---

## 2. Signos de octava (Sección I.B) — CRÍTICO PARA LA FSM

Según la regla 1-8, las octavas se numeran del 1 al 7 comenzando por el do más grave del piano de siete octavas; cada octava va de do al si ascendente más próximo. La cuarta octava contiene el Do central.

### Regla 1-9 — Colocación y signos de octava

El signo de octava se coloca inmediatamente antes de la nota a la que afecta, sin que entre ambos pueda aparecer ningún otro signo. Signos verificados contra el Ejemplo 1-9 del Manual:

| Octava | Puntos | Unicode | Rango |
| --- | --- | --- | --- |
| 1ª | 4 | ⠈ | Do1–Si1 (grave extrema) |
| 2ª | 4-5 | ⠘ | Do2–Si2 |
| 3ª | 4-5-6 | ⠸ | Do3–Si3 |
| 4ª (central) | 5 | ⠐ | Do4–Si4 |
| 5ª | 4-6 | ⠨ | Do5–Si5 |
| 6ª | 5-6 | ⠰ | Do6–Si6 |
| 7ª | 6 | ⠠ | Do7–Si7 (aguda extrema) |

### Regla 1-10 — Cuándo se indica la octava

La primera nota de una pieza o de un párrafo debe estar precedida de su signo de octava. Para las demás notas:

| Caso del Manual | Intervalo con la nota previa | ¿Se emite signo? |
| --- | --- | --- |
| (a) | menor que 4ª (unísono, 2ª, 3ª) | **NO** |
| (b) | 4ª o 5ª, misma octava | **NO** |
| (b) | 4ª o 5ª, octava distinta | **SÍ** |
| (c) | 6ª, 7ª o mayor | **SIEMPRE** |

Casos adicionales en que el sistema emite siempre el signo, cada uno con su propia regla del Manual: tras el signo de mano al inicio de renglón (regla 15-3), tras un signo de cópula (regla 5-11) y tras una doble barra (regla 9-3, aplicable cuando se emitan secciones).

Pseudocódigo de la FSM (estado `octava_actual`, implementado en `fsm.OctaveState`):

```
al procesar nueva_nota:
  # intervalo musical: unísono = 1, por eso se suma 1 a la distancia diatónica
  intervalo = |grado(nueva_nota) - grado(nota_previa)| + 1
  if es_inicio_pieza or es_inicio_renglon or es_inicio_voz_de_copula:
      emitir signo_octava(nueva_nota.octava)
  elif intervalo <= 3:
      pass                                  # caso (a)
  elif intervalo in (4, 5):
      if nueva_nota.octava != octava_previa:
          emitir signo_octava(nueva_nota.octava)   # caso (b)
  else:
      emitir signo_octava(nueva_nota.octava)       # caso (c)
```

En los acordes, el intervalo melódico se mide entre las **notas escritas** consecutivas (regla 5-6, sección 4).

---

## 3. Alteraciones, armadura e indicación de compás (Sección III, Tabla 3)

### Regla 3-1 — Colocación de las alteraciones

Las alteraciones accidentales se colocan antes de la nota o intervalo al que afectan; entre la alteración y la nota solo puede intercalarse el signo de octava. Signos de la Tabla 3:

| Alteración | Puntos | Unicode |
| --- | --- | --- |
| Sostenido (♯) | 1-4-6 | ⠩ |
| Bemol (♭) | 1-2-6 | ⠣ |
| Becuadro (♮) | 1-6 | ⠡ |
| Doble sostenido | 1-4-6, 1-4-6 | ⠩⠩ |
| Doble bemol | 1-2-6, 1-2-6 | ⠣⠣ |

### Vigencia de las alteraciones dentro del compás (Sección III.A, sin número de regla propio)

Como en la escritura en tinta, una alteración accidental afecta a todas las notas de la misma altura tonal (misma letra y misma octava) durante el resto del compás. El Manual asume esta convención de la tinta sin asignarle regla numerada; el sistema la implementa como estado de la FSM. Al iniciar un nuevo compás la vigencia se reinicia a la armadura, y la cancelación de una alteración vigente se hace con el becuadro explícito.

Pseudocódigo (estado `alteraciones_vigentes: dict[(nota, octava), alteracion]`, implementado en `fsm.AccidentalState`):

```
al inicio de compas (y de cada voz de cópula, regla 5-14):
  alteraciones_vigentes = copia(armadura_activa)

al procesar nota (n, oct):
  alt_esperada = alteraciones_vigentes.get((n, oct), NATURAL)
  if nota.alteracion != alt_esperada:
      emitir simbolo(nota.alteracion)   # puede ser becuadro para cancelar
      alteraciones_vigentes[(n, oct)] = nota.alteracion
```

Excepción implementada: la continuación de una ligadura de prolongación no repite la alteración salvo en renglón nuevo (regla 6-10, sección 6).

### Regla 3-3 — Armadura de la clave

La armadura refleja el número de alteraciones, no las notas a las que afectan: hasta tres alteraciones se repite el signo (ej. ⠩⠩ para dos sostenidos); con cuatro o más se escribe el número seguido del signo (ej. ⠼⠙⠣ para cuatro bemoles). Implementada en `braille_tables.key_signature`.

### Regla 3-6 — Indicación de compás

Las indicaciones de compás con dos cifras se escriben con el signo de número (⠼, puntos 3-4-5-6), el numerador en la posición normal de la celdilla y el denominador en la parte baja (ej. 4/4 → ⠼⠙⠲). Implementada en `braille_tables.time_signature`.

### Regla 3-8 — Agrupación de armadura y compás

La armadura de la clave y la indicación de compás se agrupan como una sola expresión al inicio de la obra (armadura primero). El sistema las emite juntas en la línea de cabecera.

---

## 4. Intervalos armónicos (Sección V.A, Tabla 5)

### Regla 5-1 — Nota escrita e intervalos según el registro

En los acordes de notas del mismo valor solo una se escribe en su forma habitual; las restantes se representan con signos de intervalo respecto de ella. En el registro agudo (mano derecha del piano) se escribe la nota **más aguda** y los intervalos se leen descendentes; en el registro grave (mano izquierda) se escribe la **más grave** y los intervalos se leen ascendentes. Signos de la Tabla 5:

| Intervalo | Puntos | Unicode |
| --- | --- | --- |
| 2ª | 3-4 | ⠌ |
| 3ª | 3-4-6 | ⠬ |
| 4ª | 3-4-5-6 | ⠼ |
| 5ª | 3-5 | ⠔ |
| 6ª | 3-5-6 | ⠴ |
| 7ª | 2-5 | ⠒ |
| 8ª (octava) | 3-6 | ⠤ |

Nota de implementación: el signo de 4ª usa la misma celda que el signo de número (regla 3-6). Se desambigua por posición: el signo de número solo precede a una cifra, mientras que el intervalo solo aparece inmediatamente después de una nota.

### Regla 5-2 — Intervalos mayores que la octava

Un intervalo superior a la 8ª se escribe con el signo del intervalo simple equivalente, precedido del signo de octava que corresponda a la nota del intervalo. Ese signo de octava es lo único que lo distingue del intervalo simple homónimo: una 9ª es «signo de octava + 2ª»; una 2ª es solo «2ª».

### Regla 5-5 — Puntillo en los acordes

Si un acorde tiene puntillo, este se coloca únicamente después de la nota escrita: los intervalos tienen siempre el mismo valor que ella.

### Regla 5-6 — Octava de la nota escrita

El intervalo melódico que forman entre sí las **notas escritas** consecutivas es el que determina si la nota escrita de un acorde necesita signo de octava (según la regla 1-10). La FSM usa como referencia la nota escrita del acorde anterior, no sus intervalos.

Fuera de alcance de esta sección: regla 5-4 (signo de octava entre dos intervalos del mismo acorde que formen unísono, 8ª o más) y reglas 5-7/5-8 (duplicación de intervalos). Documentadas como mejora pendiente.

---

## 5. In-accords / Cópulas (Sección V.B)

### Regla 5-10 — Signo de cópula total

Cuando dos o más voces simultáneas de un mismo compás no pueden representarse como intervalos (por tener ritmos distintos), se escriben sucesivamente, sin espacios intermedios, separadas por el signo de cópula total. Signos de la tabla de la sección V.B:

| Signo | Puntos | Unicode |
| --- | --- | --- |
| Cópula total | 1-2-6, 3-4-5 | ⠣⠜ |
| Cópula parcial | 5, 2 | ⠐⠂ |
| División de compás (con cópula parcial) | 4-6, 1-3 | ⠨⠅ |

La estructura del compás es: `voz_1 ⠣⠜ voz_2 [⠣⠜ voz_3 …]`

El sistema implementa solo la cópula total. La cópula parcial y la división de compás (reglas 5-16 a 5-18) quedan documentadas fuera de alcance.

### Regla 5-11 — Octava tras la cópula

La nota que sigue a un signo de cópula (o de división de compás) lleva siempre indicación de octava, igual que la primera nota del compás siguiente.

### Regla 5-12 — Orden de las voces

El orden de las voces sigue los principios de los intervalos: en mano derecha (lectura descendente) se empieza por la voz más aguda; en mano izquierda (lectura ascendente), por la más grave.

### Regla 5-14 — Las alteraciones no cruzan la cópula

Las alteraciones escritas antes de un signo de cópula **no afectan** a las notas escritas después de él: deben volver a escribirse. El sistema reinicia la vigencia de alteraciones al inicio de cada voz. Matiz pendiente: el Manual pide anteponer el punto 5 a las alteraciones (y silencios, regla 5-15) que se agregan en Braille sin figurar en la partitura en tinta; con entrada de audio no existe «tinta» de referencia, por lo que el sistema no emite ese punto 5. Documentado como limitación.

---

## 6. Ligaduras (Sección VI, Tabla 6)

### Regla 6-2 — Ligadura de expresión corta (hasta cuatro notas)

El signo de ligadura de expresión, puntos 1-4 (⠉), se utiliza para ligaduras que abarcan un máximo de cuatro notas y se coloca **después de cada nota, excepto la última**.

### Regla 6-3 — Ligadura de expresión larga (más de cuatro notas)

Dos formas admitidas: (a) duplicar el signo ⠉⠉ tras la primera nota y escribirlo sencillo tras la penúltima; (b) colocar el signo de apertura ⠰⠃ (puntos 5-6, 1-2) antes de la primera nota y el de cierre ⠘⠆ (puntos 4-5, 2-3) después de la última. El sistema implementa la forma (b), que la regla 6-4 declara preferible.

En los acordes, la ligadura de expresión se coloca después de la nota escrita y antes de los intervalos (regla 6-8, uso de España).

### Regla 6-9 — Ligadura de prolongación (tie)

Los signos de prolongación se usan cuando la ligadura en tinta une notas del mismo nombre y sonido. Signos de la Tabla 6 B:

| Signo | Puntos | Unicode |
| --- | --- | --- |
| Prolongación de nota única | 4, 1-4 | ⠈⠉ |
| Prolongación de acorde | 4-6, 1-4 | ⠨⠉ |

El signo se coloca **después de la primera nota o de su puntillo**; las ligaduras de expresión preceden a la de prolongación. Cuando la ligadura cruza la barra, se emite antes de la barra y la nota destino no lleva signo de continuación. Esto es lo que permite al cuantizador representar duraciones que no caben en una sola figura: una nota de cinco semicorcheas se escribe como negra ligada a semicorchea, y una nota que cruza la barra se parte en dos figuras ligadas sin perder duración.

Reglas asociadas implementadas: 6-10 (la alteración de una nota ligada al compás siguiente solo se repite si este inicia renglón Braille — uso de España), 6-11 (si solo una nota del acorde se prolonga, ligadura de nota única tras la nota o intervalo afectado) y 6-12 (si todo el acorde se prolonga, ligadura de acorde ⠨⠉).

---

## 7. Barras de compás (Sección IX.A, Tabla 9 A)

### Regla 9-1 — Línea divisoria

La manera habitual de representar la línea divisoria en Braille es el **espacio en blanco** (celdilla vacía). No existe símbolo para la barra simple, salvo usos especiales.

### Signos de la Tabla 9 A (sin número de regla propio)

| Signo | Puntos | Unicode |
| --- | --- | --- |
| Doble barra gruesa (**barra final**) | 1-2-6, 1-3 | ⠣⠅ |
| Doble barra al **final de una parte o sección** | 1-2-6, 1-3, 3 | ⠣⠅⠄ |

Verificados visualmente contra la Tabla 9 A. Una versión anterior de este documento los tenía invertidos. El sistema emite la barra final al término de la obra; la doble barra de sección está disponible en `braille_tables.DOUBLE_BAR` pero solo se emitirá cuando el sistema produzca secciones (asociada a la regla 9-3: la primera nota tras una doble barra lleva signo de octava).

Los signos de repetición (IX.B y IX.C) quedan fuera de alcance: el sistema emite los compases repetidos de forma expandida.

---

## 8. Formato Bar-over-bar / Compás sobre compás (Sección XIV.C.1)

Formato estándar en España para música de teclado (regla 14-15); es el modo de renderizado del sistema.

### Regla 14-16 — Estructura de paralelas

Se agrupan tantas líneas como pentagramas tiene el original: en piano, cada «paralela» consta de dos líneas, mano derecha arriba y mano izquierda debajo.

### Regla 14-17 — Alineación vertical

El primer signo de cada compás debe ocupar el mismo espacio en la línea Braille en todos los pentagramas de la paralela (complementada por la regla 14-20: varios compases por paralela, siempre que quepan completos en la línea).

### Regla 14-18 — Indicativo de parte

Los tres primeros espacios de cada línea se destinan al indicativo de la parte; en piano, los signos de mano (sección 9). El sistema emite signo de mano (2 celdas) + celda en blanco.

### Regla 14-22 — Línea guía

Cuando un compás de una parte ocupa menos espacio que el de la otra, el espacio sobrante se rellena con una **línea guía formada por el punto 3** (⠄), innecesaria cuando el compás afectado es el último de la paralela. Implementada en el renderizador.

Pseudocódigo del renderizador:

```
para cada grupo de N compases de la paralela:
  para i en range(N):
    ancho = max(len(compas_md[i]), len(compas_mi[i]))
    if i < N - 1:                       # regla 14-22
        rellenar la mano corta con ⠄ hasta ancho
  emitir signo_mano_derecha + blanco + compases_md separados por blanco
  emitir signo_mano_izquierda + blanco + compases_mi separados por blanco
  emitir linea en blanco                # separador de paralelas
```

El número N de compases por paralela es decisión de transcripción (no regla del Manual); el sistema usa N = 4 por defecto, configurable por partitura.

---

## 9. Signos de mano para piano (Sección XV)

### Regla 15-2 — Colocación de los signos de mano

Los signos de mano se colocan antes del primer signo del fragmento al que afectan:

* Mano derecha: puntos 4-6, 3-4-5 (⠨⠜)
* Mano izquierda: puntos 4-5-6, 3-4-5 (⠸⠜)

En Bar-over-bar se emiten al inicio de cada línea de la paralela (regla 14-18).

### Regla 15-3 — Octava tras el signo de mano

La nota siguiente a un signo de mano debe estar precedida de su signo de octava, sin importar la regla 1-10. El traductor reinicia la FSM de octavas al inicio de cada renglón.

---

## 10. Categorización de errores para el cálculo del BSA

Para clasificar las desviaciones sintácticas en la validación (Fase 5) se emplean las siguientes categorías, alineadas con las secciones anteriores:

| Categoría | Reglas cubiertas | Peso sugerido en el BSA |
| --- | --- | --- |
| Notas y duraciones | 1-1, 1-2, 1-3, 1-6 | 25% |
| Signos de octava | 1-9, 1-10 | 20% |
| Alteraciones y armadura | 3-1, 3-3, 3-6, 3-8 | 15% |
| Intervalos | 5-1, 5-2, 5-5, 5-6 | 10% |
| In-accords | 5-10, 5-11, 5-12, 5-14 | 10% |
| Ligaduras | 6-2, 6-3, 6-9 | 5% |
| Barras y compases | 9-1, Tabla 9 A | 5% |
| Bar-over-bar | 14-16, 14-17, 14-18, 14-22 | 5% |
| Signos de mano | 15-2, 15-3 | 5% |

Los pesos son orientativos y se ajustarán en Fase 5 en función de la frecuencia observada de cada categoría de error sobre el conjunto de validación integral.

## 11. Trazabilidad con las historias de usuario

| Regla | Historia de usuario | Épica |
| --- | --- | --- |
| 1-1, 1-2, 1-3, 1-6 | US-11 (silencios y figuras rítmicas conforme al Manual) | SCRUM-7 |
| 1-9, 1-10 | US-08 (signos de octava correctamente codificados) | SCRUM-7 |
| 3-1, 3-3, 3-6, 3-8 | US-09 (alteraciones vigentes dentro del compás) | SCRUM-7 |
| 5-1, 5-2, 5-5, 5-6, 5-10 a 5-14 | US-05 (acordes de hasta cuatro voces) + US-10 | SCRUM-6, SCRUM-7 |
| 6-2, 6-3, 6-9 | US-11 (ligaduras dentro de la categoría de figuras) | SCRUM-7 |
| 9-1, Tabla 9 A | US-07 (formato BRF estándar) | SCRUM-7 |
| 14-16, 14-17, 14-18, 14-22 | US-10 (formato Bar-over-bar con manos alineadas) | SCRUM-7 |
| 15-2, 15-3 | US-10 (formato Bar-over-bar) | SCRUM-7 |

### Trazabilidad con las pruebas unitarias

Correspondencia entre cada regla implementada y la clase de prueba que la verifica. El código no repite estos números: la auditoría regla ↔ prueba se hace desde esta tabla.

| Regla | Clase de prueba | Archivo |
| --- | --- | --- |
| 1-1, 1-2 | `TestBrfMapping`, `TestQuantize` | `test_translator.py`, `test_amt.py` |
| 1-9, 1-10 | `TestOctaveRules`, `TestCompoundIntervals` | `test_translator.py` |
| Vigencia de alteraciones (III.A) | `TestAccidentalRules` | `test_translator.py` |
| 3-3 | `TestKeySignature` | `test_translator.py` |
| 5-1 | `TestChordIntervals` | `test_translator.py` |
| 5-2 | `TestCompoundIntervals` | `test_translator.py` |
| 5-10, 5-11, 5-12 | `TestInAccords` | `test_translator.py` |
| 5-14 | `TestInAccordAccidentals` | `test_translator.py` |
| 6-2, 6-3, 6-8 | `TestSlurs`, `TestMusicXMLLigaduras` | `test_translator.py` |
| 6-9, 6-11, 6-12 | `TestTies` | `test_translator.py` |
| 6-10 | `TestTieContinuationAccidental`, `TestQuantize` | `test_translator.py`, `test_amt.py` |
| 9-1, Tabla 9 A | `TestBarSigns`, `TestBarOverBar` | `test_translator.py` |
| 14-17, 14-22 | `TestBarOverBar` | `test_translator.py` |
| 14-18, 15-2, 15-3 | `TestLineBreakOctave` | `test_translator.py` |
| Validez del BRF de salida | `TestBrfWrap`, `TestValidateBrf` | `test_translator.py`, `test_api.py` |

## 12. Fuera de alcance — Documentado para futuras iteraciones

* Claves (II): el sistema asume clave de Sol para mano derecha y clave de Fa para mano izquierda por defecto; en Braille los signos de clave son informativos (regla 2-1).
* Signos de valor mayor/menor y separación de valores (1-3): documentados arriba; aún no emitidos.
* Compás de espera abreviado con número (1-6, forma b): los compases vacíos se emiten expandidos.
* Grupos rítmicos con signos de agrupación (IV): tresillos y demás grupos irregulares se representan por sus notas individuales.
* Regla 5-4 (octava entre intervalos del mismo acorde) y duplicación de intervalos (5-7, 5-8, 5-13).
* Cópula parcial y división de compás (5-16 a 5-21); punto 5 ante alteraciones/silencios agregados en Braille (5-14, 5-15).
* Signos de doble figura (V.C, reglas 5-22 y siguientes).
* Trémolos (VII), digitación (VIII), matices (X), adornos (XI): categorías expresivas no esenciales para la lectura del texto musical.
* Repeticiones (IX.B, IX.C): se expanden en el pipeline antes de la generación del AST.
* Teoría, bajo cifrado, análisis armónico (XII); notación moderna (XIII).
* Signos de pedal Braille específicos (XV, 15-11 a 15-22): el pedal se representa únicamente por su efecto en la duración de las notas (US-06).
* Instrumentos distintos del piano (XVI en adelante): adaptación futura documentada en US-25.
