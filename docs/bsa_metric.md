# Exactitud de Símbolo Braille (BSA) — Procedimiento de medición

Este documento especifica cómo el sistema mide la calidad del archivo BRF que produce, comparándolo contra una transcripción de referencia. Es el procedimiento que responde al quinto objetivo específico del proyecto y la métrica cuyo umbral (≥ 70 %) fija el objetivo general.

Implementación: `src/evaluation/bsa.py`. Pruebas: `tests/test_bsa.py`.

## 1. Por qué hace falta una métrica propia

Las métricas consolidadas de Transcripción Musical Automática (F1 de onset, F1 a nivel de nota, *Note Error Rate*) evalúan exclusivamente la etapa acústica: miden si el modelo acertó las alturas y los tiempos, no si el archivo que lee el músico es correcto. Del otro lado, los traductores a musicografía Braille de la literatura (BrailleMUSE, BMML) no reportan ningún indicador cuantitativo sobre el código que generan.

La consecuencia práctica es que un sistema puede exhibir un F1 excelente y entregar una partitura inservible sin que ninguna métrica publicada lo detecte. El BSA cubre ese hueco: evalúa el artefacto final —el BRF— como un todo, y desagrega el error por categoría sintáctica para poder decir *en qué* falla la traducción, no solo *cuánto*.

## 2. Definición

Sean `R` la secuencia de celdas Braille de la transcripción de referencia y `G` la del archivo generado. Tras alinear ambas secuencias, se cuentan:

- **aciertos** (`A`): celdas emparejadas e idénticas.
- **sustituciones** (`S`): celdas emparejadas pero distintas.
- **omisiones** (`D`): celdas de `R` sin pareja en `G`.
- **inserciones** (`I`): celdas de `G` sin pareja en `R`.

El BSA global es la proporción de celdas coincidentes respecto de la secuencia más larga:

```
BSA = A / max(|R|, |G|)
```

Se divide entre el máximo de ambas longitudes, y no entre `|R|`, para que la métrica quede acotada en el intervalo [0, 1] y penalice las inserciones. Una definición del tipo `1 − (S+D+I)/|R|` puede volverse negativa cuando el sistema emite mucho ruido, lo que dificulta la interpretación y la comparación entre fragmentos.

Se cumple, por construcción:

```
A + S + D = |R|        A + S + I = |G|
```

Ambas identidades se verifican en las pruebas.

## 3. Procedimiento

El cálculo tiene tres pasos.

### 3.1 Clasificación de celdas

Cada celda de ambos textos se etiqueta con una de las nueve categorías sintácticas del subset implementado (ver `braille_rules_subset.md`, sección 10). La clasificación recorre el texto de izquierda a derecha reconociendo primero los símbolos de varias celdas y luego las celdas sueltas.

Los símbolos multicelda se reconocen **enteros pero se contabilizan celda a celda**, cada una heredando la categoría del símbolo. Así el conteo sigue siendo por celdas —como exige la definición— sin que un signo de mano (⠨⠜) se descomponga erróneamente en un signo de octava más otra cosa.

El orden de reconocimiento es del símbolo más largo al más corto. Esto resuelve los solapamientos por prefijo: la doble barra de sección (⠣⠅⠄) se reconoce antes que la barra final (⠣⠅), que a su vez se reconoce antes que el bemol suelto (⠣).

### 3.2 Reglas de desambiguación

El código Braille musical reutiliza celdas, así que la categoría no siempre se deduce de la celda aislada. Las ambigüedades relevantes y su resolución:

| Celda | Lecturas posibles | Regla aplicada |
| --- | --- | --- |
| ⠼ | signo de número / intervalo de 4ª | intervalo si la celda anterior es nota o intervalo; si no, signo de número |
| ⠄ | puntillo / línea guía de relleno / final de doble barra | puntillo tras nota o intervalo; parte de la doble barra si el símbolo largo ya encajó; línea guía en cualquier otro caso |
| ⠙ ⠑ ⠋ ⠛ ⠓ ⠊ ⠚ | corcheas / cifras | cifra solo dentro de una indicación numérica abierta por ⠼; en cualquier otro caso, nota |
| ⠈ ⠨ ⠰ ⠘ | signos de octava / primera celda de una ligadura o signo de mano | el símbolo de dos celdas gana si encaja completo |

Estas reglas son deterministas y quedan cubiertas por pruebas unitarias específicas. Las celdas que no encajan en ninguna categoría se etiquetan como `desconocido` y se reportan aparte: su presencia indica una laguna del clasificador, no un error de la traducción.

### 3.3 Alineación

Las dos secuencias se alinean con **distancia de edición de Levenshtein**, calculada con el algoritmo de Wagner-Fischer y recuperando el camino óptimo por retroceso. El coste es 1 para sustitución, inserción y omisión, y 0 para coincidencia.

Se eligió una alineación exacta, y no una heurística de bloques como la de `difflib`, porque el número de operaciones es el que alimenta la métrica: una alineación subóptima inflaría artificialmente el conteo de errores y haría el resultado dependiente de la implementación.

El coste es O(|R|·|G|) en tiempo y memoria. Para los fragmentos del conjunto de validación esto es holgado; el parámetro `max_cells` (4 000 000 por omisión, equivalente a unas 2000 × 2000 celdas) aborta con un mensaje explícito si se intenta comparar obras completas, en cuyo caso conviene medir paralela por paralela.

### 3.4 Atribución del error

Cada operación se atribuye a una categoría: las coincidencias, sustituciones y omisiones a la categoría de la celda **de la referencia**; las inserciones a la de la celda **generada**, que es la única disponible. El BSA por categoría se calcula con la misma fórmula restringida a las celdas de esa categoría.

## 4. BSA ponderado

Además del BSA global se reporta un promedio ponderado por categoría, con los pesos de `braille_rules_subset.md`:

| Categoría | Peso |
| --- | :---: |
| Notas y duraciones | 25 % |
| Signos de octava | 20 % |
| Alteraciones y armadura | 15 % |
| Intervalos | 10 % |
| In-accords | 10 % |
| Ligaduras | 5 % |
| Barras y compases | 5 % |
| Bar-over-bar | 5 % |
| Signos de mano | 5 % |

Solo entran las categorías **presentes en la referencia**, y los pesos se renormalizan sobre ellas. Un fragmento sin in-accords no debe quedar penalizado por una categoría que no aparece.

La motivación del ponderado es que el BSA global trata todas las celdas por igual, cuando su impacto en la lectura no lo es: un signo de octava omitido desplaza toda una frase, mientras que una línea guía de relleno mal puesta no altera el significado musical. **Ambos valores se reportan siempre**, porque el global es el más directo de interpretar y el ponderado el más fiel al efecto sobre el lector. Los pesos son la hipótesis actual y se ajustarán en la fase de validación según la frecuencia observada de cada categoría de error.

## 5. Uso

Comparar dos archivos, en BRF o en Braille Unicode indistintamente:

```
PYTHONPATH=src python -m evaluation referencia.brf generado.brf
PYTHONPATH=src python -m evaluation referencia.brf generado.brf --json
```

Salida sobre un caso con dos errores inyectados:

```
BSA global      : 96.72%
BSA ponderado   : 97.90%
celdas ref/gen  : 61 / 60
aciertos        : 59
sustituciones   : 1
omisiones       : 1
inserciones     : 0

categoria        ref   gen    ok  sust   omi   ins      BSA
notas             28    27    26     1     1     0   92.86%
octavas            6     6     6     0     0     0  100.00%
...
```

Desde Python:

```python
from evaluation import compare_files, compute_bsa
resultado = compare_files("referencia.brf", "generado.brf")
print(resultado.bsa, resultado.weighted_bsa)
```

## 6. Validación de la propia métrica

El módulo se prueba inyectando errores conocidos sobre una salida correcta y comprobando que los detecta, los cuenta y los atribuye a la categoría debida: una octava omitida debe producir exactamente una omisión en `octavas`, una nota cambiada una sustitución en `notas`, una barra sobrante una inserción en `barras`. También se verifican las identidades de conteo de la sección 2 y las reglas de desambiguación de la 3.2.

Conviene subrayar qué valida esto y qué no: comprueba que **la métrica está bien implementada**, no que el sistema traduzca bien. Medir la calidad de la traducción exige referencias humanas y es el objeto de la fase de validación.

## 7. Limitaciones

- **La métrica no es simétrica en su interpretación.** Las inserciones se atribuyen a la categoría de la celda generada, que puede no corresponder a lo que el transcriptor humano escribió en ese punto.
- **Una alineación óptima no siempre es la musicalmente evidente.** Cuando hay varios caminos de coste mínimo se toma uno de ellos, lo que puede repartir el error entre categorías de forma distinta a como lo haría un analista humano. El efecto sobre el BSA global es nulo, y sobre el desglose por categoría, marginal.
- **Diferencias legítimas de transcripción cuentan como error.** El Manual admite alternativas en varios puntos —la ligadura larga puede escribirse de dos formas, el número de compases por paralela es decisión del transcriptor—, y una referencia que elija la otra opción penalizará al sistema aunque ambas sean correctas. Al comparar contra referencias humanas conviene registrar estos casos por separado.
- **No mide legibilidad.** El BSA compara con una referencia; no dice si el resultado es cómodo de leer al tacto. Esa dimensión requeriría evaluación con usuarios.
