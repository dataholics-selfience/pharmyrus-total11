# Railway Dockerfile para Playwright
FROM python:3.11-slim-bullseye

# Instalar dependências do sistema para Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxshmfence1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar arquivos
COPY requirements.txt .
COPY src/ ./src/
COPY main.py .

# Instalar Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright browsers COM dependências do sistema
RUN playwright install --with-deps chromium

# Expor porta
EXPOSE 8080

# Comando de início
CMD ["uvicorn", "src.api_service:app", "--host", "0.0.0.0", "--port", "8080"]
