"""Compara dos archivos Braille y reporta el BSA.

    python -m evaluation referencia.brf generado.brf
"""
import argparse
import json
import sys

from .bsa import compare_files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="evaluation", description="Calcula el BSA entre dos archivos Braille")
    parser.add_argument("referencia", help="BRF de referencia (transcriptor humano)")
    parser.add_argument("generado", help="BRF producido por el sistema")
    parser.add_argument("--json", action="store_true", help="salida en JSON")
    args = parser.parse_args(argv)

    result = compare_files(args.referencia, args.generado)

    if args.json:
        print(json.dumps({
            "bsa": result.bsa,
            "bsa_ponderado": result.weighted_bsa,
            "celdas_referencia": result.total_ref,
            "celdas_generado": result.total_hyp,
            "aciertos": result.matches,
            "sustituciones": result.substitutions,
            "omisiones": result.deletions,
            "inserciones": result.insertions,
            "por_categoria": {
                cat: {"ref": s.ref, "gen": s.hyp, "aciertos": s.matches,
                      "sustituciones": s.substitutions, "omisiones": s.deletions,
                      "inserciones": s.insertions, "bsa": s.bsa}
                for cat, s in result.per_category.items()
            },
        }, ensure_ascii=False, indent=2))
    else:
        print(result.report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
