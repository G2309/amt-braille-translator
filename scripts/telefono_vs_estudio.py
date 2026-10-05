# Notas transcritas y ruido de fondo de las mismas obras grabadas en estudio y con teléfono; escribe results/oe2_telefono_vs_estudio.csv
import csv, json, statistics
import numpy as np
import soundfile as sf

PARES = ["minueto_sol", "clementi_1", "clementi_2", "clementi_3", "sonatina_sol_1", "sonatina_sol_2", "fur_elise", "vals_chopin", "wild_rose"]
SOLO_TELEFONO = ["czerny_1", "czerny_2", "czerny_3", "czerny_4", "czerny_5", "cinq_doigts_1", "cinq_doigts_2", "cinq_doigts_3", "stravinsky_valse"]
EXTERNAS = {"fur_elise", "vals_chopin"}


def audio_estudio(p):
    if p in EXTERNAS:
        return f"data/externo/{p}.mp3"
    return f"data/estudio_intermedio/{p}.flac" if p == "wild_rose" else f"data/estudio_intermedio/{p}.mp3"


def nivel(ruta):
    # Nivel de la música como percentil 95 del RMS por ventana de 46 ms, en dBFS
    x, sr = sf.read(ruta, always_2d=True)
    x = x.mean(axis=1)
    n = 2048
    v = x[: len(x) // n * n].reshape(-1, n)
    return float(np.percentile(20 * np.log10(np.sqrt((v ** 2).mean(axis=1)) + 1e-10), 95))


def notas(ruta):
    d = json.load(open(ruta))
    ns = sorted(d["notas"])
    dur = statistics.median(f - i for i, f, *_ in ns)
    ultima, reataques = {}, 0
    for i, f, alt, *_ in ns:
        if alt in ultima and i - ultima[alt] < 0.25:
            reataques += 1
        ultima[alt] = i
    return len(ns), dur, reataques / len(ns), d["duracion_s"]


def main():
    tareas = []
    for p in PARES:
        carpeta = "oe5_externo_notas" if p in EXTERNAS else "oe5_intermedio_notas"
        tareas.append((p, "estudio", f"results/{carpeta}/ajustado__{p}.json", audio_estudio(p)))
        tareas.append((p, "telefono", f"results/oe5_telefono_notas/ajustado__{p}.json", f"data/telefono/wav/{p}.wav"))
    for p in SOLO_TELEFONO:
        tareas.append((p, "telefono_solo", f"results/oe5_telefono_notas/ajustado__{p}.json", f"data/telefono/wav/{p}.wav"))
    filas = []
    for p, fuente, nota, audio in tareas:
        n, dur, rea, seg = notas(nota)
        filas.append({"pieza": p, "fuente": fuente, "duracion_s": round(seg, 1), "notas": n, "notas_por_segundo": round(n / seg, 2),
                      "duracion_mediana_s": round(dur, 3), "reataques": round(rea, 3), "nivel_musica_db": round(nivel(audio), 1)})
        print(filas[-1], flush=True)
    with open("results/oe2_telefono_vs_estudio.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    for fuente in ("estudio", "telefono", "telefono_solo"):
        v = [f for f in filas if f["fuente"] == fuente]
        print(fuente, {k: (round(statistics.median(f[k] for f in v), 3), min(f[k] for f in v), max(f[k] for f in v))
                       for k in ("notas_por_segundo", "duracion_mediana_s", "reataques", "nivel_musica_db")})


if __name__ == "__main__":
    main()
