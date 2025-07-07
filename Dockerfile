FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretórios necessários
RUN mkdir -p logs config

# Railway usa a variável PORT automaticamente
EXPOSE $PORT

# Comando para iniciar (Railway injeta a variável PORT)
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
