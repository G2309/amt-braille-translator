# Transcribe en CPU una carpeta de WAV con el modelo ajustado y guarda las notas en el formato de los notebooks
import json, sys, time
from pathlib import Path
import torch
sys.path.insert(0, "src")
from amt.transcriber import AMTTranscriber

entrada, salida, modelo = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "ajustado"
torch.set_num_threads(8)
salida.mkdir(parents=True, exist_ok=True)
tr = AMTTranscriber(checkpoint_path=modelo)
for wav in sorted(entrada.glob("*.wav")):
    destino = salida / f"{modelo}__{wav.stem}.json"
    if destino.exists():
        continue
    t0 = time.time()
    r = tr.transcribe(str(wav))
    notas = [[n.onset_s, n.offset_s, n.midi_pitch, n.velocity] for n in r.notes]
    destino.write_text(json.dumps({"pieza": wav.stem, "archivo": wav.name, "modelo": modelo, "duracion_s": r.duration_s,
                                   "latencia_s": time.time() - t0, "notas": notas,
                                   "pedal": [[p.onset_s, p.offset_s] for p in r.pedals]}))
    print(wav.stem, len(notas), "notas", round(time.time() - t0, 1), "s", flush=True)
