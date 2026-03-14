FROM ubuntu:22.04

# Evitar prompts durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Clonar whisper.cpp
RUN git clone https://github.com/ggerganov/whisper.cpp.git

# Compilar whisper.cpp
WORKDIR /app/whisper.cpp
RUN cmake -B build && cmake --build build --config Release

# Descargar modelo por defecto (se puede sobrescribir con volumen)
RUN mkdir -p /app/models && \
    wget -q -O /app/models/ggml-large-v3-turbo.bin \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin || \
    echo "Modelo no descargado, se debe montar como volumen"

# Exponer puerto
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Comando por defecto
CMD ["./build/bin/whisper-server", "-m", "/app/models/ggml-large-v3-turbo.bin", "--port", "8080", "--host", "0.0.0.0"]
