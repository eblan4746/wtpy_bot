# Telegram Bot
API_TOKEN = "ВАШ_TELEGRAM_BOT_TOKEN"
REQUIRED_CHANNEL = "@ваш_канал"  # Канал для подписки
ADMIN_ID = 123456789  # Ваш ID (узнать через @userinfobot)

# DeepSeek API (ротация ключей)
DEEPSEEK_API_KEYS = [
    "ключ1",
    "ключ2",
    "ключ3"
]
DEEPSEEK_PROMPT = "Напиши одно случайное сообщение для WhatsApp группы. Сообщение должно быть коротким (1-2 предложения) и на русском языке."

# Настройки прогрева
MESSAGES_PER_HOUR = 5  # Сообщений в час
TARIFFS = [1, 3, 5, 10]  # Доступные тарифы (часы)
MAX_DAILY_HOURS = 15  # Макс. часов прогрева в сутки

# Лимиты
DAILY_USAGE_FILE = "daily_usage.json"  # Файл для учёта использования