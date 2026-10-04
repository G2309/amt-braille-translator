# Evalua las grabaciones con telefono y sus pares de estudio con la configuracion base y la del pipeline; escribe results/oe5_telefono.csv
import csv, glob, json, sys
from functools import partial
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, "src")
from amt.postprocess import drop_octave_ghosts, split_hands_viterbi
from evaluation.components import components
from evaluation.reference import parse_reference
from evaluation.reference_eval import evaluate_piece

CONF = {
    "base": dict(legato=0.5),
    "pipeline": dict(legato=0.75, pre=partial(drop_octave_ghosts, ratio=1.0, window_s=0.05),
                     hands=partial(split_hands_viterbi, beam=1, span_weight=4.0), track=True, grouping=True, drop_penalty=2.0),
}
# clave: (carpeta de la referencia, codigo BrailleOrch, pieza dentro del archivo, anacrusa en negras, notas de estudio o None)
OBRAS = {
    "minueto_sol": ("externo2", "Bor087", 0, 1.0, "oe5_intermedio_notas"),
    "clementi_1": ("externo2", "Bor360", 0, 0.0, "oe5_intermedio_notas"),
    "clementi_2": ("externo2", "Bor360", 1, 0.0, "oe5_intermedio_notas"),
    "clementi_3": ("externo2", "Bor360", 2, 0.0, "oe5_intermedio_notas"),
    "sonatina_sol_1": ("externo2", "Bor361", 0, 0.0, "oe5_intermedio_notas"),
    "sonatina_sol_2": ("externo2", "Bor361", 1, 1.5, "oe5_intermedio_notas"),
    "wild_rose": ("externo2", "Bor194", 0, 0.0, "oe5_intermedio_notas"),
    "fur_elise": ("externo", "Bor001", 0, 0.5, "oe5_externo_notas"),
    "vals_chopin": ("externo", "Bor343", 0, 1.0, "oe5_externo_notas"),
    "stravinsky_valse": ("externo2", "Bor386", 0, 0.0, None),
    "cinq_doigts_1": ("externo2", "Bor385", 0, 0.0, None),
    "cinq_doigts_2": ("externo2", "Bor385", 1, 1.0, None),
    "cinq_doigts_3": ("externo2", "Bor385", 2, 0.0, None),
    **{f"czerny_{k}": ("externo2", "Bor374", k, 0.0, None) for k in range(1, 6)},
}

def medir(tarea):
    clave, fuente, conf = tarea
    carpeta, bor, k, anac, estudio = OBRAS[clave]
    ref = parse_reference(open(glob.glob(f"data/{carpeta}/{bor}/*.brf")[0], encoding="latin-1").read())[k]
    notas = "oe5_telefono_notas" if fuente == "telefono" else estudio
    d = json.load(open(f"results/{notas}/ajustado__{clave}.json"))
    ev = evaluate_piece(ref, d["notas"], d["duracion_s"], pickup_quarters=anac, **CONF[conf])
    c = components(ev)
    return {"pieza": clave, "fuente": fuente, "configuracion": conf, "duracion_s": round(d["duracion_s"], 1),
            "repeticiones": ev.repeats, "bsa": round(c.bsa, 4), "bsa_sin_fraseo": round(c.bsa_without_phrasing, 4),
            "f1_notas_por_compas": round(c.note_f1, 4), "alturas": round(c.pitch, 4), "ritmo": round(c.rhythm, 4)}

if __name__ == "__main__":
    tareas = [(c, "telefono", conf) for c in OBRAS for conf in CONF if Path(f"results/oe5_telefono_notas/ajustado__{c}.json").exists()]
    tareas += [(c, "estudio", conf) for c, v in OBRAS.items() if v[4] for conf in CONF]
    with Pool(14) as pool:
        filas = pool.map(medir, tareas)
    with open("results/oe5_telefono.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    for f in sorted(filas, key=lambda x: (x["pieza"], x["fuente"], x["configuracion"])):
        print(f"{f['pieza']:17s} {f['fuente']:9s} {f['configuracion']:9s} BSA {100*f['bsa']:5.1f}  F1 {100*f['f1_notas_por_compas']:5.1f}  alturas {100*f['alturas']:5.1f}  ritmo {100*f['ritmo']:5.1f}")
