FROM python:3.10-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY . .

# Создаём необходимые директории
RUN mkdir -p assets/downloads assets/output assets/temp assets/music assets/stock_videos

# Expose порт Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Запуск приложения
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]