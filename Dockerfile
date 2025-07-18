# Используем мультистадийный сборку для уменьшения размера образа
# ==============================================================

# 🛠️ Этап 1: Сборка зависимостей Node.js
FROM node:18-alpine AS node-builder
WORKDIR /app
COPY package.json .
RUN npm install --production

# 🐍 Этап 2: Сборка Python-зависимостей
FROM python:3.10-slim AS python-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 🚀 Финальный образ
FROM python:3.10-slim
WORKDIR /app

# Копируем установленные зависимости
COPY --from=node-builder /app/node_modules ./node_modules
COPY --from=python-builder /root/.local /root/.local

# Копируем исходный код
COPY . .

# Добавляем пути Python в PATH
ENV PATH=/root/.local/bin:$PATH

# Устанавливаем права для сессий WhatsApp
RUN mkdir -p /app/sessions && chmod 777 /app/sessions

# Запускаем бота
CMD ["sh", "-c", "python bot.py"]