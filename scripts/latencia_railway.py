# Latencia del pipeline desplegado en Railway con los mismos cortes de latencia_cpu.py; uso: python scripts/latencia_railway.py [URL]
import csv, json, sys, time, urllib.request
from pathlib import Path

API = sys.argv[1] if len(sys.argv) > 1 else "https://api-production-a3fc.up.railway.app"
SALIDA = Path("results/oe4_latencia_railway.csv")


def pedir(metodo, ruta, datos=None, cabeceras=None):
    req = urllib.request.Request(API + ruta, data=datos, method=metodo, headers=cabeceras or {})
    with urllib.request.urlopen(req, timeout=900) as r:
        return r.read()


def multiparte(ruta_audio, campos):
    limite = "----amtbraille"
    partes = [f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in campos.items()]
    partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="{ruta_audio.name}"\r\n'
                  f"Content-Type: audio/wav\r\n\r\n".encode() + ruta_audio.read_bytes() + b"\r\n")
    return b"".join(partes) + f"--{limite}--\r\n".encode(), {"Content-Type": f"multipart/form-data; boundary={limite}"}


def main():
    # El primer pedido despierta el contenedor si estaba dormido
    t0 = time.time(); pedir("GET", "/health"); arranque = time.time() - t0
    print(f"health {arranque:.1f} s", flush=True)
    filas = []
    for dur in (30, 60, 120, 300):
        datos, cab = multiparte(Path(f"data/cpu/corte_{dur}.wav"), {"tempo_bpm": 70, "beats": 3, "beat_type": 8})
        t0 = time.time()
        trabajo = json.loads(pedir("POST", "/transcriptions", datos, cab))
        while trabajo["status"] not in ("done", "error"):
            time.sleep(2)
            trabajo = json.loads(pedir("GET", f"/transcriptions/{trabajo['id']}"))
        total = time.time() - t0
        filas.append({"duracion_audio_s": dur, "servidor_s": round(trabajo["latency_s"], 2), "cociente_servidor": round(trabajo["latency_norm"], 3),
                      "extremo_a_extremo_s": round(total, 2), "cociente_extremo": round(total / dur, 3),
                      "dentro_de_umbral": trabajo["latency_norm"] <= 1.5, "brf_valido": trabajo["brf_valid"], "estado": trabajo["status"]})
        print(filas[-1], flush=True)
    with SALIDA.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    print(f"arranque_s {arranque:.1f}; escrito {SALIDA}")


if __name__ == "__main__":
    main()
