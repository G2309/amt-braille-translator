# API de audio a BRF para despliegue en CPU (Railway, Hugging Face Spaces u otro servicio de contenedores)
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# PyTorch solo para CPU, mucho mas liviano que la version con CUDA
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
# El checkpoint ajustado queda dentro de la imagen para que el arranque en frio no lo descargue
RUN PYTHONPATH=src python -c "from amt.transcriber import resolve_checkpoint; print(resolve_checkpoint('ajustado'))"

ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.app:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]
