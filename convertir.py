# Convierte una grabacion de piano en un archivo BRF desde la terminal
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

FORMATOS_DIRECTOS = {".mp3", ".wav", ".flac"}


def leer_compas(texto: str):
    # "3/4" a (3, 4)
    try:
        beats, beat_type = (int(x) for x in texto.split("/"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"compás inválido: {texto!r}, se espera por ejemplo 3/4")
    if beats <= 0 or beat_type not in (1, 2, 4, 8, 16, 32):
        raise argparse.ArgumentTypeError(f"compás inválido: {texto!r}")
    return beats, beat_type


def a_wav(audio: Path, carpeta: Path) -> Path:
    # Otros formatos, como el M4A del telefono, pasan por ffmpeg a WAV antes de transcribir
    if audio.suffix.lower() in FORMATOS_DIRECTOS:
        return audio
    if shutil.which("ffmpeg") is None:
        sys.exit(f"{audio.suffix} necesita ffmpeg instalado para convertirse a WAV")
    destino = carpeta / (audio.stem + ".wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(audio), "-ac", "1", "-ar", "44100", str(destino)], check=True)
    return destino


def argumentos(argv=None):
    p = argparse.ArgumentParser(description="Convierte audio de piano en musicografía Braille (BRF).")
    p.add_argument("audio", type=Path, help="grabación en MP3, WAV, FLAC u otro formato que lea ffmpeg, como M4A")
    p.add_argument("salida", type=Path, nargs="?", help="archivo BRF; por omisión, el nombre del audio con .brf")
    p.add_argument("--tempo", type=float, default=60.0, help="negras por minuto de partida (60)")
    p.add_argument("--compas", type=leer_compas, default=(4, 4), help="indicación de compás, por ejemplo 3/4 (4/4)")
    p.add_argument("--armadura", type=int, default=0, help="sostenidos positivos o bemoles negativos (0)")
    p.add_argument("--modelo", choices=("ajustado", "original"), default="ajustado", help="checkpoint del modelo acústico")
    p.add_argument("--compases-por-linea", type=int, default=None, help="compases por paralela del formato compás sobre compás")
    p.add_argument("--voces", action="store_true", help="separa voces con in-accord en compases polifónicos")
    p.add_argument("--ligaduras", action="store_true", help="infiere ligaduras de expresión del legato")
    p.add_argument("--tempo-fijo", action="store_true", help="no sigue el pulso del intérprete")
    return p.parse_args(argv)


def main(argv=None) -> None:
    a = argumentos(argv)
    from amt import AMTTranscriber
    from braille_translator.renderer import DEFAULT_MEASURES_PER_LINE
    from pipeline import audio_to_brf

    if not a.audio.exists():
        sys.exit(f"no existe {a.audio}")
    salida = a.salida or a.audio.with_suffix(".brf")
    with tempfile.TemporaryDirectory() as tmp:
        audio = a_wav(a.audio, Path(tmp))
        audio_to_brf(str(audio), str(salida), tempo_bpm=a.tempo, beats=a.compas[0], beat_type=a.compas[1],
                     fifths=a.armadura, measures_per_line=a.compases_por_linea or DEFAULT_MEASURES_PER_LINE,
                     transcriber=AMTTranscriber(checkpoint_path=a.modelo), voices=a.voces, slurs=a.ligaduras,
                     track=not a.tempo_fijo)
    print(f"BRF escrito en {salida}")


if __name__ == "__main__":
    main()
