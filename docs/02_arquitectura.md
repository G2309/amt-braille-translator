# Arquitectura

En este documento explico cómo está construido el sistema, qué estilo de arquitectura sigue, qué patrones de diseño usé y por qué. Lo escribí pensando en quien quiera modificarlo o desplegarlo.

## Resumen

El sistema es una aplicación cliente-servidor. El cliente es una aplicación web progresiva escrita en Flutter, que se publica como sitio estático. El servidor es una API REST escrita en Python con FastAPI, que envuelve un pipeline de procesamiento en forma de tuberías y filtros. Dentro del servidor el código está organizado como un monolito modular en capas, donde cada paquete de dominio tiene una responsabilidad y no conoce a los demás.

| Aspecto | Decisión |
| --- | --- |
| Estilo general | Cliente-servidor con frontend y backend desplegados por separado |
| Comunicación | HTTP con JSON, petición asíncrona con consulta periódica del estado |
| Backend | Monolito modular en capas |
| Procesamiento | Tuberías y filtros, una etapa por módulo |
| Estado de los trabajos | En memoria del proceso, sin base de datos |
| Ejecución del modelo | Una sola instancia por proceso, cargada la primera vez que se usa |
| Despliegue | Contenedor Docker para la API y sitio estático para el cliente |

## Vista de contexto

```mermaid
flowchart LR
    P["Persona usuaria con o sin discapacidad visual"]
    S["amt-braille-translator"]
    G["Grabación de piano en MP3, WAV, FLAC o M4A"]
    B["Partitura en Braille en formato BRF"]
    D["Línea Braille, impresora Braille o lector de pantalla"]

    P -->|aporta| G
    G -->|entra a| S
    S -->|produce| B
    B -->|se lee en| D
    P -->|usa| D
```

## Vista de contenedores y despliegue

```mermaid
flowchart TB
    subgraph Usuario["Dispositivo de la persona usuaria"]
        N["Navegador con la aplicación web progresiva"]
        LP["Lector de pantalla del sistema"]
    end

    subgraph Pages["GitHub Pages"]
        W["Archivos estáticos de Flutter web"]
    end

    subgraph Railway["Railway, contenedor Docker con 2 vCPU y 2 GB"]
        API["API FastAPI"]
        J["Registro de trabajos en memoria"]
        PL["Pipeline de audio a Braille"]
        MO["Modelo de Kong ajustado"]
        TMP["Carpeta temporal con audios y BRF"]
    end

    subgraph GitHub["GitHub"]
        REL["Release con el checkpoint del modelo"]
        CI["GitHub Actions"]
    end

    N -->|descarga la aplicación| W
    LP -->|lee el árbol de accesibilidad de| N
    N -->|sube audio, consulta estado y descarga BRF| API
    API -->|crea y consulta trabajos| J
    J -->|ejecuta en un hilo de trabajo| PL
    PL -->|transcribe con| MO
    PL -->|escribe| TMP
    REL -->|se copia en la imagen al construirla| MO
    CI -->|prueba y publica el cliente en| W
```

El cliente y la API no comparten nada más que el contrato HTTP. Puedo cambiar el cliente sin tocar el servidor y al revés. El checkpoint del modelo, de 172 MB, se descarga del release de GitHub cuando se construye la imagen Docker, así que el contenedor arranca sin depender de internet para el modelo.

## Capas del backend

```mermaid
flowchart TB
    subgraph Entrada["Capa de entrada"]
        API["api, rutas HTTP, validación del archivo y registro de trabajos"]
        CLI["convertir.py, uso desde la terminal"]
    end

    subgraph Orquestacion["Capa de orquestación"]
        PIPE["pipeline.py, encadena las etapas con sus parámetros"]
    end

    subgraph Dominio["Capa de dominio"]
        AMT["amt, audio, modelo acústico, limpieza, pulso y cuantizador"]
        BT["braille_translator, árbol de la partitura, máquina de estados, traductor, renderizador y exportador"]
        EV["evaluation, métrica BSA y lectura de referencias"]
    end

    API --> PIPE
    CLI --> PIPE
    PIPE --> AMT
    PIPE --> BT
    EV -->|reutiliza las etapas para medir| AMT
    EV -->|reutiliza el traductor| BT
```

La regla que seguí es que las dependencias solo bajan. La API conoce al pipeline, el pipeline conoce a los paquetes de dominio, y los paquetes de dominio no saben que existe una API. Por eso el mismo pipeline sirve para la API, para la terminal y para las evaluaciones, y las pruebas de la API pueden reemplazar el modelo por uno falso sin cargar PyTorch.

El contrato entre la etapa acústica y la determinista es `TranscriptionResult`, definido en `src/amt/events.py`: una lista de notas con inicio, final, altura MIDI e intensidad, más los eventos de pedal y la duración del audio. Cualquier modelo acústico que entregue esa estructura puede reemplazar al de Kong.

## Patrones de diseño

| Patrón | Dónde | Para qué |
| --- | --- | --- |
| Tuberías y filtros | `pipeline.py` y las etapas de `amt` y `braille_translator` | Cada etapa transforma una estructura bien definida y se puede probar, medir o reemplazar sola |
| Fábrica con inyección de dependencias | `create_app(transcriber_factory)` en `src/api/app.py` | Las pruebas inyectan un transcriptor falso y la API real usa el modelo de Kong |
| Instancia única perezosa | `AMTTranscriber._load` y el contenedor del transcriptor en `create_app` | El modelo se carga una sola vez por proceso y solo cuando llega el primer audio |
| Máquina de estados finitos | `OctaveState` y `AccidentalState` en `fsm.py` | Recordar la octava de la nota anterior y las alteraciones vigentes en el compás, como exige el Manual |
| Árbol de sintaxis abstracta | `model.py` | Tener la obra completa en memoria antes de escribir, para alinear las dos manos compás por compás |
| Despacho por tipo de nodo | `HandTranslator` en `translator.py` | Recorrer el árbol y llamar a la función de cada tipo de evento, con el mismo efecto que el patrón Visitor y menos código |
| Estrategias como parámetros | `quantize(hands=..., voices=...)`, `evaluate_piece(pre=..., hands=...)` | Cambiar el reparto de manos o la limpieza sin tocar el cuantizador, que es como medí cada mejora |
| Productor y consumidor | `JobStore` en `src/api/jobs.py` | La API recibe el audio y responde de inmediato, y un hilo de trabajo lo procesa |

### Sobre el singleton

No hay una clase Singleton global. Lo que hay es una instancia única del modelo por aplicación. `create_app` guarda el transcriptor en un contenedor y lo crea la primera vez que llega un audio, y `AMTTranscriber` carga los pesos en su primer uso. Lo hice así porque cargar el modelo tarda unos segundos y ocupa cerca de 1 GB de memoria, y no tenía sentido repetirlo en cada conversión. Al no ser un singleton global, las pruebas pueden crear otra aplicación con otro transcriptor sin interferir.

## El árbol de la partitura

```mermaid
classDiagram
    class Score {
        title
        beats
        beat_type
        fifths
        key_signature_alterations()
    }
    class Hand {
        side
    }
    class Measure {
        number
        voices()
    }
    class Note {
        step
        octave
        duration_type
        alter
        dots
        tie
        slur
    }
    class Chord {
        duration_type
        dots
        principal()
        secondary()
    }
    class Rest {
        duration_type
        dots
    }
    class MultiRest {
        count
    }
    Score "1" *-- "2" Hand : mano derecha y mano izquierda
    Hand "1" *-- "many" Measure : compases
    Measure "1" o-- "many" Note : eventos
    Measure "1" o-- "many" Chord : eventos
    Measure "1" o-- "many" Rest : eventos
    Measure "1" o-- "1" MultiRest : compases de espera
    Chord "1" *-- "many" Note : notas del acorde
```

Las clases del árbol son solo datos. Toda la lógica de traducción está en el traductor, que consulta la máquina de estados mientras recorre los compases. Necesité el árbol completo porque el formato compás sobre compás exige que las barras de ambas manos queden alineadas en vertical, y para saber cuánto relleno poner en una mano hay que conocer de antemano cuánto mide el mismo compás en la otra.

## Flujo de una conversión

```mermaid
sequenceDiagram
    actor U as Persona usuaria
    participant C as Aplicación web
    participant A as API
    participant J as Registro de trabajos
    participant P as Pipeline

    U->>C: elige la grabación, el tempo, el compás y la armadura
    C->>A: envía el audio con los parámetros
    A->>A: valida extensión y tamaño
    A->>J: crea el trabajo en espera
    A-->>C: responde con el identificador del trabajo
    J->>P: procesa en un hilo de trabajo
    Note over C: la región viva anuncia que el audio fue recibido
    loop cada dos segundos
        C->>A: pregunta por el estado
        A-->>C: en espera, procesando, listo o error
    end
    P-->>J: deja el BRF, la latencia y la validación
    C->>A: pide el BRF
    A-->>C: entrega el archivo
    Note over C: la región viva anuncia que el archivo está listo y se descarga
```

Elegí este esquema de petición asíncrona con consulta periódica porque una conversión puede tardar varios minutos en CPU. Una petición que esperara todo ese tiempo se cortaría en muchos proxies, y el usuario no tendría cómo saber en qué va el proceso.

## Ciclo de vida de un trabajo

```mermaid
stateDiagram-v2
    [*] --> EnEspera : la API recibe el audio
    EnEspera --> Procesando : el hilo de trabajo lo toma
    Procesando --> Listo : el pipeline escribe un BRF
    Procesando --> Error : falla la conversión del audio o el pipeline
    Listo --> [*] : el cliente descarga el BRF
    Error --> [*] : el cliente muestra el mensaje
```

En el código los estados se llaman `queued`, `processing`, `done` y `error`. Cada trabajo guarda además la duración del audio, la latencia, el cociente entre ambas, si el audio está dentro del alcance de cinco minutos y si el BRF pasó la validación.

## Cliente

El cliente está escrito en Flutter y se compila a web. Lo publiqué como aplicación web progresiva para que se pueda instalar desde el navegador en una computadora o en un teléfono, sin tiendas de aplicaciones.

```mermaid
flowchart TB
    M["main.dart, aplicación y tema según el modo"]
    CM["ControladorModo, guarda el modo elegido"]
    SM["Pantalla de selección de modo"]
    CV["Pantalla de conversión"]
    AC["ApiCliente, envío, estado y descarga"]
    DS["Descarga del BRF en el navegador"]

    M -->|lee y escucha| CM
    M -->|sin modo elegido muestra| SM
    M -->|con modo elegido muestra| CV
    SM -->|guarda el modo en| CM
    CV -->|habla con la API mediante| AC
    CV -->|entrega el archivo con| DS
```

La accesibilidad está en la estructura de la interfaz y no es una capa aparte. Cada control tiene una etiqueta semántica, la pantalla de conversión es la región principal, las secciones son encabezados numerados y el estado del trabajo es una región viva que el lector de pantalla anuncia sin mover el foco.

## Integración y entrega continuas

```mermaid
flowchart LR
    D["Push a dev o main"]
    T["Workflow pruebas, suite en Python 3.10, 3.12 y 3.13"]
    CL["Workflow cliente, análisis, pruebas de accesibilidad y compilación web"]
    GP["GitHub Pages"]
    RW["Railway"]

    D --> T
    D --> CL
    CL -->|solo desde main| GP
    D -->|Railway construye la imagen desde dev| RW
```

Cada cambio corre las 249 pruebas de Python y las pruebas de accesibilidad del cliente. GitHub Pages publica el cliente desde `main`. Railway construye la imagen de la API cada vez que cambian `src`, `requirements.txt` o el `Dockerfile` en `dev`; en [Operación, seguridad y KPIs](08_operacion_seguridad_y_kpis.md) recomiendo moverlo a `main`.
