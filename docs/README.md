# Documentación de amt-braille-translator

Esta carpeta reúne la documentación técnica y de operación del sistema que convierte grabaciones de piano en partituras de musicografía Braille. La escribí para que cualquiera que llegue al repositorio entienda qué hace el sistema, cómo está construido, qué resultados obtuvo, qué decisiones tomé en el camino y cómo seguirlo.

## Por dónde empezar

| Documento | Qué responde |
| --- | --- |
| [01 Visión general](01_vision_general.md) | Qué es el sistema, por qué escogí el tema y cómo funciona de principio a fin |
| [02 Arquitectura](02_arquitectura.md) | Componentes, capas, patrones de diseño, flujo de una conversión y despliegue |
| [03 Resultados](03_resultados.md) | Qué se midió en cada objetivo y qué valores obtuve |
| [04 Pivotes](04_pivotes.md) | Los cambios que hice respecto al plan y por qué |
| [05 Instalación y despliegue](05_instalacion_y_despliegue.md) | Cómo correrlo en una computadora, en un teléfono y en la nube |
| [06 Presupuesto](06_presupuesto.md) | Cuánto cuesta operarlo y qué alternativas gratuitas existen |
| [07 Escalabilidad y futuro](07_escalabilidad_y_futuro.md) | Hasta dónde escala hoy, cómo seguir escalando, qué faltó y cómo mejorarlo |
| [08 Operación, seguridad y KPIs](08_operacion_seguridad_y_kpis.md) | Visión de administrador de sistemas con ITIL y DevOps, seguridad y métricas de seguimiento |
| [09 Preguntas frecuentes](09_preguntas_frecuentes.md) | Respuestas directas a las preguntas de la presentación |

## Documentos de referencia técnica

| Documento | Contenido |
| --- | --- |
| [Revisión de literatura AMT](literature_review_amt.md) | Modelos de transcripción evaluados y el benchmark que llevó a elegir el modelo de Kong |
| [Subconjunto de reglas Braille](braille_rules_subset.md) | Las 28 reglas del Manual de Aller Pérez que implementa el traductor, con su trazabilidad a pruebas |
| [Pipeline determinista](deterministic_pipeline.md) | Cuantizador, árbol de sintaxis abstracta, máquina de estados, traductor, renderizador y exportador |
| [Métrica BSA](bsa_metric.md) | Definición de la Exactitud de Símbolo Braille, su desglose y la evaluación contra referencias humanas |

## Convenciones

- Los diagramas están en Mermaid, así que GitHub los muestra directamente.
- Los datos que respaldan cada cifra están en la carpeta `results/` del repositorio, y su origen está descrito en `results/README.md`.
- El código vive en la rama `dev`, esta documentación en la rama `docs` y las versiones liberadas en `main`.
