# ===========================
# 1. Imagem base
# ===========================
FROM python:3.11-slim

# Evita mensagens interativas
ENV DEBIAN_FRONTEND=noninteractive

# ===========================
# 2. Instalar dependências do sistema
# ===========================
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ===========================
# 3. Criar diretório do app
# ===========================
WORKDIR /app

# ===========================
# 4. Copiar arquivos do projeto
# ===========================
COPY . /app

# ===========================
# 5. Instalar dependências Python
# ===========================
RUN pip install --no-cache-dir -r requirements.txt

# ===========================
# 6. Expor porta do Streamlit
# ===========================
EXPOSE 8501

# ===========================
# 7. Configurações Streamlit para produção
# ===========================
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_SERVER_HEADLESS=true

# ===========================
# 8. Comando de execução
# ===========================
CMD ["streamlit", "run", "hub.py", "--server.port=8501", "--server.address=0.0.0.0"]
