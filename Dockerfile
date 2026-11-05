# 1. Imagem base oficial, estavel e leve
FROM python:3.12-slim

# 2. Instala dependencias do sistema operacional necessarias para audio (ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# 3. Cria e define o diretorio de trabalho da aplicacao
WORKDIR /app

# 4. Instala a versao PyTorch otimizada para CPU (evita baixar gigabytes de pacotes CUDA)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 5. Copia e instala as dependencias Python (aproveitando o cache de camadas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia todo o codigo-fonte da aplicacao e os testes
COPY . .

# 7. Configuracoes de ambiente para Python e cache de modelos de IA
ENV PYTHONPATH=/app/src \
    HF_HOME=/cache/huggingface \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 8. Comando padrao de execucao: roda os testes unitarios
CMD ["pytest"]
