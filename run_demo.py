"""
Uso:  python run_demo.py [entrada.musicxml] [salida.brf]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from braille_translator import musicxml_to_brf, braille_tables as bt

if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else "examples/simple_piece.musicxml"
    out = sys.argv[2] if len(sys.argv) > 2 else "output.brf"

    braille = musicxml_to_brf(inp, out)

    print("Braille Unicode (formato Bar-over-bar) \n")
    print(braille)
    print("\n Version BRF (Braille ASCII) \n")
    print(bt.unicode_to_brf(braille))
    print(f"\nArchivo BRF escrito en: {out}")
