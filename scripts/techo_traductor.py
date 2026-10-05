# Techo del traductor: la partitura MusicXML de la misma edición traducida y comparada con el Braille humano; escribe results/oe5_techo_traductor.csv
import copy, csv, sys
sys.path.insert(0, "src")
from braille_translator.model import Score
from braille_translator.musicxml_parser import parse_musicxml
from braille_translator.translator import translate_score
from evaluation.bsa import compute_bsa
from evaluation.reference import parse_reference, reference_streams
from evaluation.reference_eval import MAX_CELLS, merge

# Primer compás de cada pieza dentro del MusicXML completo de las Goldberg
CORTES = [0, 32, 64, 98, 114, 148, 180, 216, 248, 280, 296, 328, 360, 392, 424, 456, 488,
          538, 570, 602, 634, 666, 682, 714, 746, 778, 812, 844, 876, 908, 940, 958, 990]
DESARROLLO = set(range(16)) | {31}
PIEZAS = [i for i in range(32) if i != 25]


def pieza(completa, ref, i):
    s = Score(beats=ref.beats, beat_type=ref.beat_type, fifths=ref.fifths)
    s.right.measures = copy.deepcopy(completa.right.measures[CORTES[i]:CORTES[i + 1]])
    s.left.measures = copy.deepcopy(completa.left.measures[CORTES[i]:CORTES[i + 1]])
    return s


def main():
    refs = parse_reference(open("data/goldberg.brf").read())
    completa = parse_musicxml("data/ogv_xml/score.xml")
    filas = []
    for i in PIEZAS:
        ref = reference_streams(refs[i], False)
        fila = {"pieza": f"goldberg_{i:02d}", "particion": "desarrollo" if i in DESARROLLO else "prueba"}
        for nombre, agrupar in (("sin_agrupacion", False), ("con_agrupacion", True)):
            der, izq = translate_score(pieza(completa, refs[i], i), measures_per_line=1, grouping=agrupar)
            b = merge(compute_bsa(ref.right, "".join(der), MAX_CELLS), compute_bsa(ref.left, "".join(izq), MAX_CELLS))
            fila[f"bsa_{nombre}"] = round(b.bsa, 4)
        filas.append(fila)
    with open("results/oe5_techo_traductor.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    for part in ("desarrollo", "prueba"):
        v = [f for f in filas if f["particion"] == part]
        print(part, len(v), *(round(100 * sum(f[k] for f in v) / len(v), 2) for k in ("bsa_sin_agrupacion", "bsa_con_agrupacion")),
              "min", round(100 * min(f["bsa_con_agrupacion"] for f in v), 1), "max", round(100 * max(f["bsa_con_agrupacion"] for f in v), 1))


if __name__ == "__main__":
    main()
