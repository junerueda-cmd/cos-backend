# Imagen base ligera de Python
FROM python:3.11-slim

# Dependencias del sistema que necesita el motor de conversión (pdf2docx/opencv)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    fonts-dejavu \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# La plataforma (Render/Railway) inyecta el puerto en la variable PORT
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
