# Preguntas frecuentes

Respuestas directas a las preguntas que espero en la presentación. Cada una enlaza al documento donde está el detalle.

## ¿Por qué escogí este tema?

Porque una persona ciega que quiere estudiar piano depende de que alguien haya transcrito la obra a Braille, y la mayor parte del repertorio no lo está. Transcribir a mano tarda semanas y requiere especialistas. En cambio, casi todo el repertorio está grabado. Quise atacar justo el tramo que faltaba, de la grabación a la partitura Braille, combinando lo que sé de redes neuronales con lo que sé de compiladores. Además, en la literatura no encontré una forma de medir qué tan cerca queda una partitura Braille generada de la de un transcriptor, y eso me pareció un aporte en sí mismo. Más contexto en [Visión general](01_vision_general.md).

## ¿Qué arquitectura tiene? ¿Usa un singleton?

Es una aplicación cliente-servidor. El cliente es una aplicación web progresiva en Flutter y el servidor es una API en FastAPI que envuelve un pipeline de tuberías y filtros, organizado como un monolito modular en capas. No hay una clase Singleton global; el modelo se carga una sola vez por proceso, la primera vez que se usa, y se inyecta con una fábrica para poder reemplazarlo en las pruebas. También uso una máquina de estados finitos para las octavas y alteraciones, un árbol de sintaxis abstracta para la partitura y un esquema productor y consumidor para los trabajos. Detalle en [Arquitectura](02_arquitectura.md).

## ¿Cuáles fueron sus limitantes?

| Limitante | Efecto |
| --- | --- |
| Trabajé solo, a tiempo parcial, en dieciséis semanas | Prioricé un sistema completo y medido sobre funciones adicionales; ver [Pivotes](04_pivotes.md) |
| Cómputo gratuito con cuota semanal de GPU en Kaggle | Corridas de ajuste acotadas a 3.5 horas y notebooks reanudables |
| Pocos pares de grabación y partitura Braille de la misma obra | Reuní 32 piezas de Goldberg y 10 obras de BrailleOrch, más 18 grabaciones mías |
| El modelo no estima tempo, compás ni armadura | La persona usuaria los indica |
| Sin participantes con discapacidad visual dentro del plazo | Evalué la accesibilidad con herramientas automáticas y TalkBack |
| Sin equipos Windows ni Apple | No probé NVDA ni VoiceOver |
| Las grabaciones de teléfono en casa tienen ruido de fondo | El ajuste fino con degradaciones simuladas no alcanza para ellas |

## ¿Por qué no se alcanzó el 70 % de exactitud?

Porque el error se origina antes del traductor. Cuando le doy al mismo traductor la partitura correcta, alcanza 89.1 % y 78.8 % en las dos particiones de Goldberg. Desde audio queda en 33.2 % en la partición de prueba. La diferencia está en las notas que el modelo omite o agrega, en el orden de las notas dentro de cada mano y en la conversión de tiempos a figuras. Las mejoras del cuantizador subieron entre 9 y 16 puntos, pero no alcanzan para cerrar esa brecha. Detalle en [Resultados](03_resultados.md).

## ¿Cuál es el presupuesto?

El desarrollo no tuvo costo en dinero salvo Railway: usé Kaggle, GitHub y software libre gratuitos. La API en Railway cuesta 5 USD al mes con el plan Hobby, que incluye 5 USD de uso. Si el contenedor pasa todo el mes despierto con el modelo cargado, el costo sube a unos 12 USD. Una grabación de cinco minutos cuesta cerca de 0.004 USD de cómputo. Para no pagar nada, la API puede ir a Hugging Face Spaces y el cliente seguir en GitHub Pages, o todo puede correr en una computadora local. Detalle en [Presupuesto](06_presupuesto.md).

## ¿Es escalable?

Escala verticalmente: con más núcleos baja la latencia, de 1.21 veces la duración del audio con 2 núcleos a 0.89 con 8 y a 0.08 con una GPU. Escala a cero, porque el contenedor duerme sin tráfico. El cliente escala sin límite práctico por ser estático. No escala horizontalmente todavía, porque los trabajos y los archivos viven en la memoria de un proceso. Fue una decisión consciente para terminar a tiempo, ya que el sistema está pensado para una computadora local. Para escalar horizontalmente basta mover los trabajos a Redis o PostgreSQL, los archivos a un almacenamiento de objetos y el procesamiento a trabajadores con una cola. Detalle en [Escalabilidad y futuro](07_escalabilidad_y_futuro.md).

## ¿Corre en un teléfono?

La aplicación sí: la probé completa con TalkBack en Android, usando la API en Railway. También se puede usar una computadora de la casa como servidor y el teléfono como cliente en la misma red. Procesar el audio dentro del propio teléfono no lo probé; en Android parece posible con Termux y una distribución Debian, con las ruedas oficiales de PyTorch para Arm, aunque lento; en iOS no es práctico. Detalle en [Instalación y despliegue](05_instalacion_y_despliegue.md).

## ¿Qué KPIs, métricas y seguimiento tiene?

Mido la calidad con la Exactitud de Símbolo Braille y su desglose, el desempeño con el cociente entre tiempo de proceso y duración del audio, la confiabilidad con la proporción de trabajos sin error y de BRF válidos, la capacidad con la memoria frente al límite, el costo por grabación y la accesibilidad con las pruebas automáticas y TalkBack. Cada trabajo de la API ya guarda su latencia y su validación. Para el seguimiento continuo propongo un monitor externo de `/health`, registros estructurados y repetir los scripts de medición en cada liberación. Detalle en [Operación, seguridad y KPIs](08_operacion_seguridad_y_kpis.md).

## ¿Qué tan seguro es?

Tiene HTTPS, CORS restringido al cliente, una lista de formatos permitidos, un límite de 100 MB por archivo, identificadores aleatorios para los trabajos, ningún dato personal almacenado y el modelo verificado con su hash. Le faltan autenticación y límite de peticiones, un usuario sin privilegios en el contenedor, borrado de archivos por tiempo y análisis de vulnerabilidades de las dependencias. Para un prototipo de un solo usuario el riesgo es bajo, pero los resolvería antes de compartirlo ampliamente. Detalle en [Operación, seguridad y KPIs](08_operacion_seguridad_y_kpis.md).

## ¿Qué alternativas e investigaciones anteriores hay?

| Trabajo | Qué hace | Por qué no resuelve el problema |
| --- | --- | --- |
| Onsets and Frames, Hawthorne y otros, 2018 | Transcribe piano de audio a notas | Entrega notas en segundos, no una partitura ni Braille |
| Kong y otros, 2021 | Transcripción de piano de alta resolución con pedal | Es el modelo que uso; por sí solo no escribe partituras |
| MT3 y hFT-Transformer | Transcripción con transformers | Mismo límite; MT3 además no estima el pedal |
| BrailleMUSE, Goto y otros, 2007 | Traduce MusicXML a Braille musical | Necesita una partitura digital limpia, con voces y figuras resueltas |
| BMML, Bortolazzi y otros, 2008 | Lenguaje de marcado para partituras Braille | Es un formato de intercambio, no un motor automático |
| GOODFEEL de Dancing Dots, Braille Music Editor | Herramientas comerciales de transcripción | Parten de partituras digitales y requieren un transcriptor |

Ninguno conecta la grabación con la partitura Braille ni mide el resultado contra un transcriptor humano. Mi sistema toma el modelo de Kong como primera etapa, la idea de una representación intermedia de BMML para el árbol de la partitura y la traducción determinista de BrailleMUSE, y agrega el tramo intermedio y la métrica. Más detalle en [Revisión de literatura](literature_review_amt.md).

## ¿Cómo implementaría las recomendaciones?

| Recomendación | Implementación concreta | Esfuerzo |
| --- | --- | --- |
| Unir fragmentos de una misma nota | Filtro en `postprocess.py` que una ataques de la misma tecla separados por menos de un umbral, elegido con la partición de desarrollo | Días |
| Límite de gasto y API gratuita | Fijar el límite en Railway y publicar la misma imagen en Hugging Face Spaces | Horas |
| Seguridad básica | Usuario sin privilegios en el `Dockerfile`, límite de peticiones con slowapi, borrado de archivos a la hora y `pip-audit` en Actions | Días |
| Despliegue desde main | Cambiar la rama de origen del servicio en Railway | Minutos |
| Ajuste con grabaciones reales | Grabar con un teléfono mientras un piano digital registra el MIDI, y repetir el ajuste fino con esos pares | Semanas |
| Reparto de manos aprendido | Clasificador pequeño entrenado con partituras donde cada nota tiene su mano | Semanas |
| Escalado horizontal | Estado en Redis, archivos en almacenamiento de objetos y cola con Celery; detalle en [Escalabilidad y futuro](07_escalabilidad_y_futuro.md) | Semanas |
| Evaluación con personas | Sesiones con estudiantes ciegos de piano y un docente, con el recorrido del flujo y la lectura del BRF en una línea Braille | Semanas |

## ¿Cómo lo vería un administrador de sistemas?

Como un servicio pequeño con un catálogo de un solo servicio, una cadena de cambios por ramas con pruebas automáticas, un despliegue reproducible con Docker y un modelo de capacidad medido. Ya pasé por un incidente real, la latencia de 17 veces por los hilos de PyTorch, y por un problema de dependencias, ambos diagnosticados, resueltos y documentados. Lo que le falta para operar en producción es monitoreo externo, límites de uso, configuración de Railway como código y desplegar solo versiones liberadas. Detalle en [Operación, seguridad y KPIs](08_operacion_seguridad_y_kpis.md).

## ¿Cuál es el futuro del proyecto?

Lo veo como una herramienta de apoyo para docentes y estudiantes: un primer borrador que se corrige mucho más rápido que transcribir desde cero, y una forma de conocer obras que no existen en Braille. A corto plazo atacaría las grabaciones de teléfono y el reparto de manos, a mediano plazo la evaluación con personas usuarias y la estimación de tempo, compás y armadura, y a largo plazo un modelo para teléfonos y más reglas del Manual. Al ser código abierto, la métrica y las referencias que reuní pueden servir a otros. Detalle en [Escalabilidad y futuro](07_escalabilidad_y_futuro.md).
