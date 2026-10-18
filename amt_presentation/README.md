# amt_presentation

Página de la defensa del trabajo de graduación. Funciona como página que se recorre con scroll y como presentación de pantalla completa.

## Uso

| Tecla | Acción |
| --- | --- |
| P o F5 | Entrar al modo presentación; P o Esc salen. F5 es el botón de inicio del control de KDE Connect |
| Flechas, espacio, Re Pág y Av Pág | Avanzar o retroceder una sección; en cada resultado la flecha primero gira la tarjeta del objetivo a su resultado, y en Diagramas y Recomendaciones recorre las láminas |
| R | Mostrar u ocultar las diapositivas de respaldo para las preguntas del jurado |
| G | Abrir o cerrar el glosario |

El tiempo total por omisión es de 30 minutos y se cambia con `?min=30` en la dirección; el reloj de cada sección se reparte según los pesos de la rúbrica (`data-peso`). Con `?presentar` la página abre directamente en modo presentación.

## Guion

`guion.html` arma el guion completo de la defensa a partir de las notas del orador de cada sección (`aside.notas`), agrupado por parte (`data-parte`) con su hora de inicio y su duración, más las respuestas de las diapositivas de respaldo. Se imprime con una parte por página. No se publica en Railway: se abre en local con `python3 -m http.server` dentro de esta carpeta.

## Contenido generado

`assets/espectrograma.png`, `assets/notas.png` y `assets/braille_fur_elise.svg` salen de `scripts/visuales_presentacion.py`, con la grabación, las notas transcritas y el traductor del propio sistema. Las capturas de teléfono vienen de `cliente/auditoria/capturas.mjs` y la figura por pieza de `notebooks/resultados-figuras.ipynb`.

## Créditos de imágenes

- «Reading Braille», Stefan Malmesjö, CC BY 2.0, https://commons.wikimedia.org/wiki/File:Reading_Braille.jpg
- «Braille music», CC0, https://commons.wikimedia.org/wiki/File:Braille_music.jpg

## Despliegue

El `Dockerfile` sirve los archivos estáticos con Caddy en el puerto `PORT`. En Railway el servicio `amt_presentation` usa esta carpeta como directorio raíz.

`assets/logo_uvg.png` es el logo institucional de la Universidad del Valle de Guatemala, tomado de su sitio web, y se usa solo para identificar el trabajo de graduación.
