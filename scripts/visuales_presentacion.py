# Visuales de la presentación con un caso real: espectrograma, notas transcritas y Braille generado de los primeros segundos de Für Elise
import json, sys
from pathlib import Path
import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, "src")
from amt.events import NoteEvent, TranscriptionResult
from braille_translator import braille_tables as bt
from pipeline import result_to_brf

SALIDA = Path("amt_presentation/assets")
INK, GRIS, NUBE, AZUL = "#222326", "#747679", "#ebf0f8", "#415eee"
SEGUNDOS = 7.0


def tramo():
    d = json.load(open("results/oe5_externo_notas/ajustado__fur_elise.json"))
    notas = sorted(d["notas"])
    inicio = notas[0][0] - 0.15
    return inicio, [n for n in notas if inicio <= n[0] < inicio + SEGUNDOS]


def espectrograma(inicio):
    x, sr = sf.read("data/externo/fur_elise.mp3", always_2d=True)
    x = x.mean(axis=1)[int(inicio * sr): int((inicio + SEGUNDOS) * sr)]
    n, salto = 4096, 256
    ventanas = np.lib.stride_tricks.sliding_window_view(x, n)[::salto] * np.hanning(n)
    mag = 20 * np.log10(np.abs(np.fft.rfft(ventanas, axis=1)).T + 1e-6)
    f = np.fft.rfftfreq(n, 1 / sr)
    sel = (f > 60) & (f < 2600)
    mapa = LinearSegmentedColormap.from_list("nube", ["#ffffff", NUBE, "#86b6ef", AZUL, INK])
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=200)
    ax.pcolormesh(np.arange(mag.shape[1]) * salto / sr, f[sel], mag[sel], cmap=mapa, vmin=mag[sel].max() - 70, vmax=mag[sel].max(), shading="auto")
    ax.set_yscale("log")
    ax.set_yticks([110, 220, 440, 880, 1760], ["La2", "La3", "La4", "La5", "La6"])
    ax.set_xlabel("segundos", color=GRIS)
    estilo(ax)
    fig.savefig(SALIDA / "espectrograma.png", bbox_inches="tight", facecolor="white")


def notas_transcritas(inicio, notas):
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=200)
    for i, f, alt, vel in notas:
        ax.add_patch(plt.Rectangle((i - inicio, alt - 0.4), max(f - i, 0.05), 0.8, color=AZUL, alpha=0.35 + 0.65 * vel / 127, lw=0))
    alturas = [n[2] for n in notas]
    ax.set_xlim(0, SEGUNDOS)
    ax.set_ylim(min(alturas) - 2, max(alturas) + 2)
    nombres = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
    marcas = [m for m in range(min(alturas) - 1, max(alturas) + 2) if m % 12 in (0, 4, 9)]
    ax.set_yticks(marcas, [f"{nombres[m % 12]}{m // 12 - 1}" for m in marcas])
    ax.set_xlabel("segundos", color=GRIS)
    estilo(ax)
    fig.savefig(SALIDA / "notas.png", bbox_inches="tight", facecolor="white")


def estilo(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#d9dde5")
    ax.tick_params(colors=GRIS, labelsize=9)


def braille(inicio, notas):
    eventos = [NoteEvent(i - inicio, f - inicio, alt, vel) for i, f, alt, vel in notas]
    r = TranscriptionResult(notes=eventos, duration_s=SEGUNDOS)
    ruta = SALIDA / "fur_elise_inicio.brf"
    result_to_brf(r, output_path=str(ruta), tempo_bpm=70, beats=3, beat_type=8, fifths=0)
    lineas = [l for l in ruta.read_text().splitlines() if l.strip()][:4]
    # Cada celda se dibuja con sus seis puntos: los presentes en Ink y los ausentes en Cloud Card
    ancho, alto, paso, r_punto = 22, 36, 12, 3.6
    cols = max(len(l) for l in lineas)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cols * ancho + 8} {len(lineas) * (alto + 14)}" role="img" aria-label="Braille generado para el inicio de Für Elise">']
    for fila, linea in enumerate(lineas):
        for col, car in enumerate(bt.brf_to_unicode(linea)):
            bits = ord(car) - 0x2800 if "⠀" <= car <= "⣿" else 0
            x0, y0 = 6 + col * ancho, 6 + fila * (alto + 14)
            for k, (dx, dy) in enumerate([(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]):
                lleno = bits >> k & 1
                svg.append(f'<circle cx="{x0 + dx * paso:.1f}" cy="{y0 + dy * paso:.1f}" r="{r_punto if lleno else 1.6}" fill="{INK if lleno else NUBE}"/>')
    svg.append("</svg>")
    (SALIDA / "braille_fur_elise.svg").write_text("\n".join(svg))
    print("\n".join(lineas))


if __name__ == "__main__":
    SALIDA.mkdir(parents=True, exist_ok=True)
    inicio, notas = tramo()
    print("inicio", round(inicio, 2), "notas", len(notas))
    espectrograma(inicio)
    notas_transcritas(inicio, notas)
    braille(inicio, notas)
