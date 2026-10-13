# amt_presentation

Página de la defensa del trabajo de graduación. Funciona como página que se recorre con scroll y como presentación de pantalla completa.

## Uso

| Tecla | Acción |
| --- | --- |
| P | Entrar o salir del modo presentación |
| Flechas, espacio, Re Pág y Av Pág | Avanzar o retroceder una sección; en Resultados recorren primero el carrusel, objetivo y luego resultado |
| N | Mostrar u ocultar las notas del orador |
| R | Mostrar u ocultar las diapositivas de respaldo para las preguntas del jurado |

Con `?min=20` en la dirección se ajusta el tiempo total; el reloj de cada sección se reparte según los pesos de la rúbrica (`data-peso`). Con `?presentar` la página abre directamente en modo presentación.

## Contenido generado

`assets/espectrograma.png`, `assets/notas.png` y `assets/braille_fur_elise.svg` salen de `scripts/visuales_presentacion.py`, con la grabación, las notas transcritas y el traductor del propio sistema. Las capturas de teléfono vienen de `cliente/auditoria/capturas.mjs` y la figura por pieza de `notebooks/resultados-figuras.ipynb`.

## Créditos de imágenes

- «Reading Braille», Stefan Malmesjö, CC BY 2.0, https://commons.wikimedia.org/wiki/File:Reading_Braille.jpg
- «Braille music», CC0, https://commons.wikimedia.org/wiki/File:Braille_music.jpg

## Despliegue

El `Dockerfile` sirve los archivos estáticos con Caddy en el puerto `PORT`. En Railway el servicio `amt_presentation` usa esta carpeta como directorio raíz.
