FROM python:3.11-slim

# Diretório padrão
WORKDIR /app

# Copia os requirements primeiro para evitar rebuilds desnecessários
COPY requirements.txt .

# Instala dependências
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos
COPY . .

# Expor a porta usada pelo Streamlit
EXPOSE 8501

# Variáveis essenciais do Streamlit
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Comando de inicialização
CMD ["streamlit", "run", "hub.py"]
