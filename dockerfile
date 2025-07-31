# Dockerfile

FROM python:3.11-slim

# Evita prompts interativos
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Instala dependências de sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libx11-dev \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório de trabalho
WORKDIR /app

# Copia dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos
COPY . .

# Comando padrão
CMD ["python", "bot_vagas_remotas_com_ads.py"]
