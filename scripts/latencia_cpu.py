# Latencia del pipeline completo en CPU; uso: python scripts/latencia_cpu.py HILOS, con taskset para fijar nucleos
import json, os, resource, sys, time
os.makedirs("data/cpu", exist_ok=True)
import numpy as np, soundfile as sf, librosa, torch
sys.path.insert(0, "src")
hilos = int(sys.argv[1]); torch.set_num_threads(hilos)
from amt.transcriber import AMTTranscriber
from pipeline import result_to_brf
base = np.concatenate([librosa.load(f, sr=44100, mono=True)[0] for f in ("data/externo/fur_elise.mp3", "data/externo/vals_chopin.mp3")])
t0 = time.time(); tr = AMTTranscriber(); carga = time.time() - t0
filas = []
for dur in (30, 60, 120, 300):
    ruta = f"data/cpu/corte_{dur}.wav"
    if not os.path.exists(ruta):
        sf.write(ruta, base[: dur * 44100], 44100)
    t0 = time.time(); r = tr.transcribe(ruta); t_amt = time.time() - t0
    t0 = time.time(); result_to_brf(r, output_path=f"data/cpu/corte_{dur}.brf", tempo_bpm=70, beats=3, beat_type=8); t_det = time.time() - t0
    filas.append({"hilos": hilos, "duracion_s": dur, "notas": len(r.notes), "amt_s": round(t_amt, 2), "determinista_s": round(t_det, 2),
                  "cociente": round((t_amt + t_det) / dur, 3)})
    print(filas[-1], flush=True)
pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(json.dumps({"hilos": hilos, "carga_modelo_s": round(carga, 1), "memoria_pico_mb": round(pico)}))
json.dump(filas, open(f"data/cpu/bench_{hilos}.json", "w"))
