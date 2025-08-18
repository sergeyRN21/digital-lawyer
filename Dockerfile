# Используем базовый образ Python
FROM python:3.9-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    wget \
    curl \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    python3-openssl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install -r requirements.txt

# Создаем директории для кэша
RUN mkdir -p /app/huggingface_cache

# Устанавливаем переменные окружения для кэша
ENV TRANSFORMERS_CACHE=/app/huggingface_cache
ENV HF_HOME=/app/huggingface_cache
ENV SENTENCE_TRANSFORMERS_HOME=/app/huggingface_cache

# Предзагрузка моделей (опционально - для ускорения первого запуска)
RUN python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('intfloat/multilingual-e5-large')"

# Копируем весь код проекта
COPY app/ ./app/

# Устанавливаем рабочую директорию
WORKDIR /app/app

# Запускаем приложение
CMD ["python", "constitution_bot.py"]