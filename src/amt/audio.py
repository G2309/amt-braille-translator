"""Normalizacion del audio antes de la transcripcion.

El modelo acustico se entreno con grabaciones de concierto a un nivel parecido
entre si. Un audio de celular puede llegar varias decenas de dB mas bajo o con
componente continua, y eso desplaza el log-mel que ve la primera capa.

Solo se corrige el nivel: quitar ruido o reverberacion aqui meteria artefactos
que el modelo tampoco vio al entrenar.
"""
import numpy as np

# RMS de los tramos con sonido en MAESTRO, medido en notebooks/amt-finetune.ipynb
TARGET_DBFS = -24.9
PEAK_CEILING = 0.99
FRAME = 2048
ACTIVE_BELOW_PEAK_DB = 40.0
SILENCE_DBFS = -80.0


def _db(x: float) -> float:
    return 20.0 * np.log10(max(x, 1e-12))


def active_rms(x: np.ndarray, frame: int = FRAME) -> float:
    """RMS de los cuadros que suenan, sin contar silencios ni colas."""
    n = len(x) // frame
    if n == 0:
        return float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0
    frames = x[: n * frame].reshape(n, frame)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    loud = rms[rms >= rms.max() * 10 ** (-ACTIVE_BELOW_PEAK_DB / 20)]
    return float(np.sqrt(np.mean(loud ** 2)))


def normalize_loudness(x: np.ndarray, target_dbfs: float = TARGET_DBFS) -> np.ndarray:
    """Lleva el audio al nivel de referencia sin recortar picos."""
    x = np.asarray(x, dtype=np.float32)
    x = x - x.mean()
    level = active_rms(x)
    if _db(level) < SILENCE_DBFS:
        return x
    gain = 10 ** ((target_dbfs - _db(level)) / 20)
    peak = float(np.abs(x).max()) * gain
    if peak > PEAK_CEILING:
        gain *= PEAK_CEILING / peak
    return (x * gain).astype(np.float32)
