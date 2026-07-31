# Subset de Reglas de Musicografía Braille — Alcance del Módulo de Traducción

Este documento define el subconjunto de reglas del Manual Simplificado de Musicografía Braille (Aller Pérez, ONCE, edición 2001) que serán implementadas por el módulo determinista de traducción (FSM + AST + renderizador Bar-over-bar) del sistema.

Las reglas se identifican por su numeración original del Manual (formato X-Y) y se agrupan por categoría sintáctica para facilitar su trazabilidad con las pruebas unitarias y con la categorización de errores del cálculo del BSA (Braille Symbol Accuracy).

Referencia bibliográfica: Aller Pérez, J. (2001). Manual Simplificado de Musicografía Braille — Versión para usuarios no ciegos. Madrid: Organización Nacional de Ciegos Españoles (ONCE). ISBN: 84-484-0240-5.

## Convenciones de notación en este documento

Para representar los símbolos Braille en texto plano se emplean tres notaciones complementarias:

* Puntos del cajetín Braille: los seis puntos del cajetín se enumeran de arriba abajo y de izquierda a derecha como 1-2-3 (columna izquierda) y 4-5-6 (columna derecha). Por ejemplo, la letra d en Braille literario ocupa los puntos 1-4-5.
* Unicode Braille: cuando sea útil, se incluye el carácter Unicode del rango U+2800–U+28FF (ej: ⠙ para los puntos 1-4-5).
* Descripción textual: para reglas condicionales complejas se acompaña la descripción en prosa.

## Alcance implementado en el sistema

El módulo de traducción implementa las siguientes categorías del Manual, en orden de prioridad para el cálculo del BSA:

1. Signos básicos de notas y silencios (Sección I.A)
2. Signos de octava (Sección I.B) — crítico para la FSM
3. Alteraciones y su vigencia dentro del compás (Sección III.A) — crítico para la FSM
4. Intervalos armónicos (Sección V.A)
5. In-accords o cópulas (Sección V.B)
6. Ligaduras de expresión y de prolongación (Sección VI)
7. Barras de compás (Sección IX.A)
8. Formato Bar-over-bar / Compás sobre compás (Sección XIV.C.1)
9. Signos de mano derecha e izquierda para piano (Sección XV.A.1)

Las secciones fuera de alcance para la versión inicial del sistema (documentadas para trazabilidad) son: claves (II), grupos rítmicos con signos de agrupación (IV), signos de doble figura (V.C), trémolos (VII), digitación (VIII), matices (X), adornos (XI), teoría y bajo cifrado (XII), notación moderna (XIII), pedal de piano en su notación Braille específica (XV.A.2) y todo lo referente a instrumentos distintos del piano (XV.B a XX).

---

## 1. Notas, figuras y silencios (Sección I.A)

### Regla 1-1 — Codificación de notas y figuras

Las siete notas Do, Re, Mi, Fa, Sol, La, Si se codifican con las letras Braille d, e, f, g, h, i, j respectivamente (puntos 1, 2, 4 y 5). La combinación adicional con los puntos 3 y 6 dentro de la misma celdilla determina la figura rítmica. Cada símbolo representa dos valores rítmicos posibles que se distinguen por contexto:

| Nota | Símbolo Braille (redonda/semicorchea) | Puntos |
| --- | --- | --- |
| Do | ⠽ | 1-3-4-5-6 |
| Re | ⠵ | 1-3-5-6 |
| Mi | ⠋ | 1-2-4 (base e sin puntillo) |
| Fa | ⠛ | 1-2-4-5 |
| Sol | ⠓ | 1-2-5 |
| La | ⠊ | 2-4 |
| Si | ⠚ | 2-4-5 |

Las duraciones se derivan añadiendo puntos 3 y 6:

| Grupo de valores | Puntos adicionales |
| --- | --- |
| Redondas y semicorcheas | 3 y 6 |
| Blancas y fusas | 3 |
| Negras y semifusas | 6 |
| Corcheas y garrapateas | ninguno |

### Regla 1-2 — Puntillo

El puntillo se representa con el punto 3 (⠄) colocado inmediatamente después de la nota o silencio afectado, sin ningún signo intercalado. El doble puntillo añade otro punto 3.

### Regla 1-3 — Signo de valor mayor / valor menor / separación

Cuando el contexto no basta para determinar si un símbolo representa el valor mayor o el menor de su par, se emplean signos especiales:

* Signo de valor mayor (aplica a redonda, blanca, negra, corchea)
* Signo de valor menor (aplica a semicorchea, fusa, semifusa, garrapatea)
* Signo de separación de valores (indica cambio dentro del compás)

### Regla 1-6 — Compás de espera (silencio prolongado)

Para representar compases completos de silencio se usa siempre el silencio de redonda:

* 2 o 3 compases consecutivos: repetición del silencio de redonda.
* 4 o más compases consecutivos: signo numérico + número de compases + silencio de redonda.

---

## 2. Signos de octava (Sección I.B) — CRÍTICO PARA LA FSM

Las octavas se numeran del 1 al 7. La cuarta octava contiene el Do central (Do4). Los signos de octava indican en qué octava se ubica una nota:

| Octava | Puntos | Unicode | Rango aproximado |
| --- | --- | --- | --- |
| 1ª | 4 | ⠈ | Do1–Si1 (grave extrema) |
| 2ª | 4-5 | ⠘ | Do2–Si2 |
| 3ª | 4-5-6 | ⠸ | Do3–Si3 |
| 4ª (central) | 5 | ⠐ | Do4–Si4 |
| 5ª | 4-6 | ⠨ | Do5–Si5 |
| 6ª | 5-6 | ⠰ | Do6–Si6 |
| 7ª | 6 | ⠠ | Do7–Si7 (aguda extrema) |

Los signos de octava se colocan inmediatamente antes de la nota a la que afectan.

### Regla 2-2 — Cuándo se coloca el signo de octava

Se coloca signo de octava en los siguientes casos, sin excepción:

1. Al inicio de una pieza (primera nota).
2. Después de una doble barra de compás.
3. Al comienzo de una nueva línea (renglón Braille).
4. Al inicio de cada compás en formato Bar-over-bar cuando cambia la voz.

### Regla 2-3 — Signo de octava entre notas consecutivas

Esta es la regla más importante para la FSM. Entre dos notas consecutivas dentro del mismo compás, el signo de octava se emite en función del intervalo entre ellas:

| Intervalo | ¿Cambia de octava? | ¿Se emite signo? |
| --- | --- | --- |
| Unísono, 2ª o 3ª | No importa | **NO** se emite |
| 4ª o 5ª | Sí | **SÍ** se emite |
| 4ª o 5ª | No | **NO** se emite |
| 6ª, 7ª o mayor | Sí o no | **SIEMPRE** se emite |

Racional del sistema: En intervalos pequeños (≤3ª) la octava es inferible por la nota anterior. En intervalos medios (4ª–5ª) es ambigua solo cuando cruza octava. En intervalos grandes (≥6ª) siempre se hace explícita.

Pseudocódigo de la FSM (estado octava_actual):

```
al procesar nueva_nota:
  # intervalo musical: unísono = 1, por eso se suma 1 a la distancia diatónica
  intervalo = |grado(nueva_nota) - grado(nota_previa)| + 1
  if es_inicio_pieza or es_inicio_linea or es_inicio_compas_bob:
      emitir signo_octava(nueva_nota.octava)
  elif intervalo <= 3:
      # no emitir signo
      pass
  elif intervalo in (4, 5):
      if nueva_nota.octava != nota_previa.octava:
          emitir signo_octava(nueva_nota.octava)
  else:  # intervalo >= 6
      emitir signo_octava(nueva_nota.octava)
  nota_previa = nueva_nota

```

### Regla 2-4 — Signo de octava después de un intervalo o al inicio de un in-accord

Después de un intervalo armónico o al comienzo de una nueva voz de in-accord, se aplican las mismas reglas de 2-3 tomando como nota de referencia la nota principal del intervalo o del acorde previo.

---

## 3. Alteraciones (Sección III.A) — CRÍTICO PARA LA FSM

### Regla 3-1 — Símbolos de las alteraciones

Las alteraciones se representan con los siguientes signos, colocados inmediatamente antes de la nota que alteran (y antes del signo de octava si existe):

| Alteración | Puntos | Unicode |
| --- | --- | --- |
| Sostenido (♯) | 1-4-6 | ⠩ |
| Bemol (♭) | 1-2-6 | ⠣ |
| Becuadro (♮) | 1-6 | ⠡ |
| Doble sostenido | 1-4-6, 1-4-6 | ⠩⠩ |
| Doble bemol | 1-2-6, 1-2-6 | ⠣⠣ |

### Regla 3-2 — Vigencia de las alteraciones dentro del compás

Al igual que en la escritura en tinta, una alteración accidental afecta a todas las notas de la misma altura tonal (misma letra y misma octava) que aparezcan en el resto del compás. La FSM debe mantener este estado y no re-emitir el símbolo de alteración para las notas ya alteradas.

Al iniciar un nuevo compás, el estado de alteraciones vigentes se reinicia a las alteraciones de la armadura de la clave.

Pseudocódigo de la FSM (estado alteraciones_vigentes: dict[(nota, octava), alteracion]):

```
al inicio de compas:
  alteraciones_vigentes = copia(armadura_activa)

al procesar nota (n, oct):
  alt_esperada = alteraciones_vigentes.get((n, oct), NATURAL)
  alt_real = nota.alteracion
  if alt_real != alt_esperada:
      emitir simbolo(alt_real)  # puede ser becuadro para cancelar
      alteraciones_vigentes[(n, oct)] = alt_real
  # si coinciden, no se emite nada

```

### Regla 3-3 — Becuadro para cancelar alteración vigente

Cuando dentro del mismo compás se requiere cancelar una alteración previamente aplicada a la misma nota+octava, se emite el becuadro (⠡) explícitamente.

### Regla 3-4 — Armadura de la clave

La armadura se representa emitiendo los símbolos de alteración de la armadura al inicio de la pieza, después de la clave (si se emite), en el orden estándar (Fa♯, Do♯, Sol♯... para sostenidos; Si♭, Mi♭, La♭... para bemoles).

---

## 4. Intervalos armónicos (Sección V.A)

### Regla 5-1 — Símbolos de intervalos

Cuando dos o más notas suenan simultáneamente, la nota principal se escribe con su símbolo completo (nota + octava + alteración si aplica) y las demás se representan como intervalos medidos desde la nota principal:

| Intervalo | Puntos | Unicode |
| --- | --- | --- |
| 2ª | 3-4 | ⠌ |
| 3ª | 3-4-6 | ⠬ |
| 4ª | 3-4-5-6 | ⠼ |
| 5ª | 3-5 | ⠔ |
| 6ª | 3-5-6 | ⠴ |
| 7ª | 2-5 | ⠒ |
| 8ª (octava) | 3-6 | ⠤ |

Nota de implementación: el signo de 4ª (3-4-5-6) usa la misma celda que el signo de número (Regla 3-6). Se desambigua por contexto: el signo de número solo precede a una cifra de compás o a un número de compás, mientras que el intervalo solo aparece inmediatamente después de una nota.

### Regla 5-1b — Intervalos mayores que la octava

Un intervalo superior a la 8ª se reduce a su equivalente simple restando séptimas y se antepone el signo de octava de la nota del intervalo. Ese signo de octava es lo único que lo distingue del intervalo simple homónimo: una 9ª es «signo de octava + 2ª» y una 2ª es solo «2ª».

### Regla 5-2 — Nota principal según la mano

* Mano derecha: la nota principal es la más aguda; los intervalos se cuentan hacia abajo.
* Mano izquierda: la nota principal es la más grave; los intervalos se cuentan hacia arriba.

### Regla 5-3 — Orden de los intervalos

Los intervalos se emiten en orden desde la nota principal hacia el extremo opuesto (descendente en mano derecha, ascendente en mano izquierda), inmediatamente después de la nota principal, sin espacios ni signos intermedios.

---

## 5. In-accords / Cópulas (Sección V.B)

### Regla 5-4 — Signo de cópula

Cuando dos o más voces melódicas ocupan el mismo compás en la misma mano y no pueden representarse como intervalos armónicos (porque tienen ritmos independientes), se separan con el signo de cópula o in-accord:

* Signo de cópula: puntos 1-2-6 (⠣)

La estructura del compás es: voz_1  ⠣  voz_2  [ ⠣  voz_3 ]

El signo de cópula usa la misma celda que el bemol (Regla 3-1) y se desambigua por posición: el bemol precede a una nota, la cópula separa dos voces completas.

> PENDIENTE DE VERIFICACIÓN contra la Tabla 5B del Manual antes de implementar la Regla 5-4. La versión anterior de este documento asignaba a la cópula los puntos 4-6 + 3-4-5, que son exactamente el signo de mano derecha de la Regla 15-1, por lo que era inutilizable. El valor 1-2-6 que aparece arriba corresponde al signo de in-accord del estándar internacional, no está confirmado contra el Manual Simplificado (ONCE, 2001) y todavía no tiene contraparte en `braille_tables.py`.

### Regla 5-5 — Signos de octava en in-accords

Al iniciar cada voz nueva después del signo de cópula se emite siempre un signo de octava para la primera nota de esa voz, sin importar las reglas 2-3.

---

## 6. Ligaduras (Sección VI)

### Regla 6-1 — Ligadura de expresión (fraseo)

La ligadura de expresión que agrupa dos o más notas se representa con el signo de puntos 1-4 (⠅) colocado antes de la primera nota afectada, y el signo de puntos 1-2-5 (⠓... con contexto) al final. En la práctica del sistema:

* Ligadura sobre 2 notas: signo simple entre las notas.
* Ligadura sobre más de 2 notas: apertura antes del primer grupo, cierre después del último.

### Regla 6-2 — Ligadura de prolongación (tie)

La ligadura de prolongación entre dos notas de la misma altura tonal se representa con el signo de puntos 4, 1-4 (⠈⠉) colocado entre las dos notas afectadas.

Cuando la ligadura de prolongación cruza una barra de compás, el signo se emite antes de la barra de compás y la nota destino en el compás siguiente no lleva signo de continuación (a diferencia del tie en tinta que se dibuja como arco).

---

## 7. Barras de compás (Sección IX.A)

### Regla 9-1 — Barra de compás simple

En musicografía Braille, la separación de compases se representa mediante un espacio en blanco (celdilla vacía) entre el último símbolo de un compás y el primero del siguiente. No existe un símbolo específico para la barra simple.

### Regla 9-2 — Barra doble

Se representa con los puntos 1-2-6, 1-3 (⠣⠅) al final del compás. Marca fin de sección.

### Regla 9-3 — Barra final

Se representa con los puntos 1-2-6, 1-3, 3 (⠣⠅⠄) o variante equivalente al final de la pieza.

### Regla 9-4 — Repeticiones (fuera de alcance en la versión inicial)

Los signos de repetición Braille (parcial, de compás completo, de varios compases, segno) se documentan en el Manual como IX.C.1–IX.C.5, pero quedan fuera del alcance de la versión inicial. El sistema emitirá los compases repetidos de forma expandida.

---

## 8. Formato Bar-over-bar / Compás sobre compás (Sección XIV.C.1)

Este es el formato estándar para música de piano y se implementa como modo de renderizado.

### Regla 14-1 — Estructura del párrafo Bar-over-bar

En Bar-over-bar, cada "párrafo" contiene:

* Una línea con el signo de mano derecha (⠨⠜) seguido de la transcripción Braille de la mano derecha para un número fijo de compases.
* Debajo, una línea con el signo de mano izquierda (⠸⠜) seguido de la transcripción de la mano izquierda para los mismos compases.
* Las barras de compás (espacios) de ambas manos deben quedar alineadas verticalmente.

### Regla 14-2 — Alineación vertical de compases

El renderizador debe calcular, para cada compás, la longitud máxima (en celdillas) entre la mano derecha y la mano izquierda, y rellenar con celdillas vacías (⠀, U+2800) la mano más corta hasta igualar la longitud. Esto garantiza que las barras (espacios entre compases) coincidan verticalmente.

Pseudocódigo del renderizador Bar-over-bar:

```
para cada grupo de N compases del párrafo:
  linea_md = signo_mano_derecha + join(compases_md, sep=" ")
  linea_mi = signo_mano_izquierda + join(compases_mi, sep=" ")

  # calcular alineación por compás
  para i en range(N):
    len_md = longitud_celdillas(compases_md[i])
    len_mi = longitud_celdillas(compases_mi[i])
    ancho = max(len_md, len_mi)
    compases_md[i] = padding_derecha(compases_md[i], ancho)
    compases_mi[i] = padding_derecha(compases_mi[i], ancho)

  emitir linea_md
  emitir linea_mi
  emitir linea_en_blanco  # separador de párrafo

```

### Regla 14-3 — Número de compases por párrafo

El número N de compases por párrafo es variable pero típicamente 4 en piezas didácticas. El sistema tomará N = 4 como valor por defecto y permitirá configurarlo por partitura.

---

## 9. Signos de mano derecha e izquierda para piano (Sección XV.A.1)

### Regla 15-1 — Signos de mano

* Mano derecha: puntos 4-6 seguido de 3-4-5 (⠨⠜)
* Mano izquierda: puntos 4-5-6 seguido de 3-4-5 (⠸⠜)

Estos signos se emiten:

* Al inicio de cada línea de mano derecha o mano izquierda en el formato Bar-over-bar.
* Al reanudar una mano después de un pasaje unísono o de una sección donde solo actuó una mano.

### Regla 15-2 — Signo de mano y octava inicial

Después del signo de mano, la primera nota siempre lleva su signo de octava explícito, sin importar la regla 2-3.

---

## 10. Categorización de errores para el cálculo del BSA

Para clasificar las desviaciones sintácticas en la validación (Fase 5) se emplean las siguientes categorías, alineadas con las secciones anteriores:

| Categoría | Reglas cubiertas | Peso sugerido en el BSA |
| --- | --- | --- |
| Notas y duraciones | 1-1, 1-2, 1-3 | 25% |
| Signos de octava | 2-2, 2-3, 2-4 | 20% |
| Alteraciones | 3-1, 3-2, 3-3, 3-4 | 15% |
| Intervalos | 5-1, 5-2, 5-3 | 10% |
| In-accords | 5-4, 5-5 | 10% |
| Ligaduras | 6-1, 6-2 | 5% |
| Barras y compases | 9-1, 9-2, 9-3 | 5% |
| Bar-over-bar | 14-1, 14-2 | 5% |
| Signos de mano | 15-1, 15-2 | 5% |

Los pesos son orientativos y se ajustarán en Fase 5 en función de la frecuencia observada de cada categoría de error sobre el conjunto de validación integral.

---

## 11. Trazabilidad con las historias de usuario

| Regla | Historia de usuario | Épica |
| --- | --- | --- |
| 1-1, 1-2, 1-3, 1-6 | US-11 (silencios y figuras rítmicas conforme al Manual) | SCRUM-7 |
| 2-2, 2-3, 2-4 | US-08 (signos de octava correctamente codificados) | SCRUM-7 |
| 3-1, 3-2, 3-3, 3-4 | US-09 (alteraciones vigentes dentro del compás) | SCRUM-7 |
| 5-1 a 5-5 | US-05 (soporte de acordes de hasta cuatro voces) + US-10 | SCRUM-6, SCRUM-7 |
| 6-1, 6-2 | US-11 (ligaduras dentro de la categoría de figuras) | SCRUM-7 |
| 9-1, 9-2, 9-3 | US-07 (formato BRF estándar) | SCRUM-7 |
| 14-1, 14-2, 14-3 | US-10 (formato Bar-over-bar con manos alineadas) | SCRUM-7 |
| 15-1, 15-2 | US-10 (formato Bar-over-bar) | SCRUM-7 |

---

## 12. Fuera de alcance — Documentado para futuras iteraciones

Las siguientes reglas del Manual quedan fuera de alcance para la versión inicial del sistema pero se documentan aquí para trazabilidad de decisiones:

* Claves (II): el sistema asume clave de Sol para mano derecha y clave de Fa para mano izquierda por defecto.
* Grupos rítmicos con signos de agrupación (IV): los tresillos, seisillos y demás grupos irregulares se representan por sus notas individuales sin el signo de agrupación específico del Manual.
* Signos de doble figura (V.C): no se emite el signo de figura duplicada; las duraciones se emiten individualmente.
* Trémolos (VII), Digitación (VIII), Matices (X), Adornos (XI): categorías expresivas no esenciales para la lectura del texto musical.
* Teoría, Bajo cifrado, Análisis armónico (XII): categorías analíticas, no de ejecución.
* Notación moderna (XIII): técnicas extendidas no habituales en el repertorio pianístico didáctico.
* Repeticiones Braille (IX.C): las repeticiones se expanden en el pipeline antes de la generación del AST.
* Signos de pedal Braille específicos (XV.A.2): el pedal se representa únicamente por su efecto en la duración de las notas (US-06), no por su símbolo Braille propio.
* Instrumentos distintos del piano (XV.B a XX): el alcance del sistema está limitado a piano; adaptación futura documentada en US-25.
