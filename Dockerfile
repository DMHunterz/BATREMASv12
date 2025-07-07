# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretórios necessários
RUN mkdir -p logs config

# Expor porta
EXPOSE 8000

# Comando para iniciar
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
