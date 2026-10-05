# BSA por categoría sintáctica con la configuración del pipeline, sumado por conjunto; escribe results/oe5_categorias_pipeline.csv
import csv, sys
from multiprocessing import Pool
sys.path.insert(0, "scripts")
sys.path.insert(0, "src")
import desglose_bsa as d

CAMPOS = ("ref", "hyp", "matches", "substitutions", "deletions", "insertions")


def medir(item):
    tipo, x = item
    if tipo == "g":
        import json
        notas = json.load(open(f"results/oe5_notas/ajustado__{x:02d}.json")); ref, anac = d.GOLDBERG[x], 0.0
    else:
        import glob, json
        nombre, carpeta, bor, k, anac = x
        ref = d.parse_reference(open(glob.glob(f"data/{carpeta}/{bor}/*.brf")[0], encoding="latin-1").read())[k]
        sub = "oe5_externo_notas" if carpeta == "externo" else "oe5_intermedio_notas"
        notas = json.load(open(f"results/{sub}/ajustado__{nombre}.json"))
    ev = d.evaluate_piece(ref, notas["notas"], notas["duracion_s"], pickup_quarters=anac, **d.CONF["pipeline"])
    return {cat: [getattr(s, c) for c in CAMPOS] for cat, s in ev.both.per_category.items()}


if __name__ == "__main__":
    filas = []
    with Pool(14) as pool:
        for conjunto, items in d.CONJUNTOS.items():
            total = {}
            for por_cat in pool.map(medir, items):
                for cat, v in por_cat.items():
                    total[cat] = [a + b for a, b in zip(total.get(cat, [0] * 6), v)]
            for cat, v in total.items():
                fila = {"conjunto": conjunto, "categoria": cat, **dict(zip(CAMPOS, v))}
                fila["bsa"] = round(v[2] / max(v[0], v[1]), 4) if max(v[0], v[1]) else 1.0
                filas.append(fila)
                print(fila, flush=True)
    with open("results/oe5_categorias_pipeline.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
