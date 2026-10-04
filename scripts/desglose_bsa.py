# Desglose del BSA desde audio por conjunto, con la configuracion base y la del pipeline; escribe results/oe5_desglose.csv
import csv, glob, json, sys
from functools import partial
from multiprocessing import Pool
sys.path.insert(0, "src")
from amt.postprocess import drop_octave_ghosts, split_hands_viterbi
from evaluation.components import components
from evaluation.reference import parse_reference
from evaluation.reference_eval import evaluate_piece

GOLDBERG = parse_reference(open("data/goldberg.brf").read())
CONF = {
    "base": dict(legato=0.5),
    "pipeline": dict(legato=0.75, pre=partial(drop_octave_ghosts, ratio=1.0, window_s=0.05),
                     hands=partial(split_hands_viterbi, beam=1, span_weight=4.0), track=True, grouping=True, drop_penalty=2.0),
}
EXTERNO = [("fur_elise", "externo", "Bor001", 0, 0.5), ("fille", "externo", "Bor195", 0, 0.0), ("vals_chopin", "externo", "Bor343", 0, 1.0)]
INTERMEDIO = [("minueto_sol", "externo2", "Bor087", 0, 1.0), ("clementi_1", "externo2", "Bor360", 0, 0.0),
              ("clementi_2", "externo2", "Bor360", 1, 0.0), ("sonatina_sol_1", "externo2", "Bor361", 0, 0.0),
              ("sonatina_sol_2", "externo2", "Bor361", 1, 1.5)]
CONJUNTOS = {"desarrollo": [("g", i) for i in list(range(16)) + [31]],
             "prueba": [("g", i) for i in range(16, 31) if i != 25],
             "externo": [("x", e) for e in EXTERNO], "intermedio": [("x", e) for e in INTERMEDIO]}

def medir(tarea):
    conf, (tipo, item) = tarea
    if tipo == "g":
        d = json.load(open(f"results/oe5_notas/ajustado__{item:02d}.json")); ref, anac, nombre = GOLDBERG[item], 0.0, f"goldberg_{item:02d}"
    else:
        nombre, carpeta, bor, k, anac = item
        ref = parse_reference(open(glob.glob(f"data/{carpeta}/{bor}/*.brf")[0], encoding="latin-1").read())[k]
        notas = "oe5_externo_notas" if carpeta == "externo" else "oe5_intermedio_notas"
        d = json.load(open(f"results/{notas}/ajustado__{nombre}.json"))
    c = components(evaluate_piece(ref, d["notas"], d["duracion_s"], pickup_quarters=anac, **CONF[conf]))
    return conf, nombre, c

if __name__ == "__main__":
    tareas = [(c, it) for c in CONF for items in CONJUNTOS.values() for it in items]
    with Pool(14) as pool:
        res = pool.map(medir, tareas)
    filas = []
    for (conf, (tipo, item)), (_, nombre, c) in zip(tareas, res):
        conjunto = next(k for k, v in CONJUNTOS.items() if (tipo, item) in v)
        filas.append({"configuracion": conf, "conjunto": conjunto, "pieza": nombre, "bsa": round(c.bsa, 4),
                      "bsa_sin_fraseo": round(c.bsa_without_phrasing, 4), "f1_notas_por_compas": round(c.note_f1, 4),
                      "alturas": round(c.pitch, 4), "ritmo": round(c.rhythm, 4)})
    with open("results/oe5_desglose.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    claves = ["bsa", "bsa_sin_fraseo", "f1_notas_por_compas", "alturas", "ritmo"]
    print(f"{'conjunto':11s} {'conf':9s} " + " ".join(f"{k:>18s}" for k in claves))
    for conjunto in CONJUNTOS:
        for conf in CONF:
            v = [f for f in filas if f["conjunto"] == conjunto and f["configuracion"] == conf]
            print(f"{conjunto:11s} {conf:9s} " + " ".join(f"{100*sum(x[k] for x in v)/len(v):17.1f}%" for k in claves))
