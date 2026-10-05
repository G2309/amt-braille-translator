# BSA por pieza con la configuración base y la del pipeline, con notas y celdas de cada lado; escribe results/oe5_por_pieza.csv
import csv, glob, json, sys
from multiprocessing import Pool
sys.path.insert(0, "scripts")
sys.path.insert(0, "src")
import desglose_bsa as d
from evaluation.components import components

# Las dos grabaciones excluidas del promedio intermedio también se reportan pieza por pieza
EXCLUIDAS = [("clementi_3", "externo2", "Bor360", 2, 0.0), ("wild_rose", "externo2", "Bor194", 0, 0.0)]
CONJUNTOS = dict(d.CONJUNTOS, excluidas=[("x", e) for e in EXCLUIDAS])


def medir(tarea):
    conf, conjunto, (tipo, x) = tarea
    if tipo == "g":
        notas = json.load(open(f"results/oe5_notas/ajustado__{x:02d}.json")); ref, anac, nombre = d.GOLDBERG[x], 0.0, f"goldberg_{x:02d}"
    else:
        nombre, carpeta, bor, k, anac = x
        ref = d.parse_reference(open(glob.glob(f"data/{carpeta}/{bor}/*.brf")[0], encoding="latin-1").read())[k]
        sub = "oe5_externo_notas" if carpeta == "externo" else "oe5_intermedio_notas"
        notas = json.load(open(f"results/{sub}/ajustado__{nombre}.json"))
    ev = d.evaluate_piece(ref, notas["notas"], notas["duracion_s"], pickup_quarters=anac, **d.CONF[conf])
    c = components(ev)
    return {"configuracion": conf, "conjunto": conjunto, "pieza": nombre, "compas": f"{ref.beats}/{ref.beat_type}",
            "duracion_s": round(notas["duracion_s"], 1), "tempo_estimado": round(ev.tempo_bpm, 1),
            "notas_transcritas": ev.notes_transcribed, "notas_referencia": ev.notes_reference,
            "celdas_referencia": ev.both.total_ref, "celdas_generadas": ev.both.total_hyp,
            "bsa": round(ev.both.bsa, 4), "f1_notas_por_compas": round(c.note_f1, 4), "alturas": round(c.pitch, 4), "ritmo": round(c.rhythm, 4)}


if __name__ == "__main__":
    tareas = [(conf, conjunto, it) for conf in d.CONF for conjunto, items in CONJUNTOS.items() for it in items]
    with Pool(14) as pool:
        filas = pool.map(medir, tareas)
    with open("results/oe5_por_pieza.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    for f in filas:
        if f["configuracion"] == "pipeline":
            print(f)
