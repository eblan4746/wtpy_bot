import os
import asyncio
import subprocess
import random
import json
import aiohttp
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_TOKEN, REQUIRED_CHANNEL, ADMIN_ID, DEEPSEEK_API_KEYS
from config import DEEPSEEK_PROMPT, MESSAGES_PER_HOUR, TARIFFS, MAX_DAILY_HOURS, DAILY_USAGE_FILE

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния
class WarmupStates:
    WAITING_GROUP_LINK = "waiting_group_link"
    WAITING_DURATION = "waiting_duration"

# Проверка подписки
async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Клавиатура выбора длительности
def duration_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(f"{h} часов", callback_data=f"dur_{h}") for h in TARIFFS]
    keyboard.add(*buttons)
    return keyboard

# Учёт дневного лимита
def check_daily_limit(duration):
    today = datetime.date.today().isoformat()
    
    if os.path.exists(DAILY_USAGE_FILE):
        with open(DAILY_USAGE_FILE, 'r') as f:
            usage_data = json.load(f)
    else:
        usage_data = {}
    
    if today not in usage_data:
        usage_data[today] = 0
    
    if usage_data[today] + duration <= MAX_DAILY_HOURS:
        usage_data[today] += duration
        with open(DAILY_USAGE_FILE, 'w') as f:
            json.dump(usage_data, f)
        return True, usage_data[today]
    return False, usage_data[today]

# Генерация AI-сообщений с ротацией ключей
async def generate_ai_messages(count):
    messages = []
    key_index = 0
    
    for i in range(count):
        # Ротация ключей
        api_key = DEEPSEEK_API_KEYS[key_index]
        key_index = (key_index + 1) % len(DEEPSEEK_API_KEYS)
        
        # Случайные параметры
        temperature = random.uniform(0.7, 0.95)
        seed = random.randint(1, 10000)
        
        # Формируем запрос
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": DEEPSEEK_PROMPT}],
            "temperature": temperature,
            "max_tokens": 100,
            "seed": seed
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.deepseek.com/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'choices' in data and data['choices']:
                            message = data['choices'][0]['message']['content'].strip()
                            messages.append(message)
                        else:
                            messages.append(f"Сообщение #{i+1} для прогрева 🌟")
                    elif response.status == 429:
                        print(f"Ключ {api_key[:5]}... исчерпал лимит")
                    else:
                        messages.append(f"Сообщение #{i+1} для чата 🔥")
        except:
            messages.append(f"Сообщение #{i+1} для общения 💬")
    
    return messages

# Команда /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer(
            f"⚠️ Для использования бота необходимо подписаться на канал: {REQUIRED_CHANNEL}",
            disable_web_page_preview=True
        )
        return
        
    await message.answer("🔗 Отправьте ссылку-приглашение в WhatsApp группу:")
    await WarmupStates.WAITING_GROUP_LINK.set()

# Обработка ссылки на группу
@dp.message_handler(state=WarmupStates.WAITING_GROUP_LINK)
async def process_group_link(message: types.Message, state: FSMContext):
    group_link = message.text.strip()
    if "https://chat.whatsapp.com/" not in group_link:
        await message.answer("❌ Некорректная ссылка! Отправьте валидную ссылку на группу WhatsApp:")
        return
        
    await state.update_data(group_link=group_link)
    await message.answer("⏱ Выберите длительность прогрева:", reply_markup=duration_keyboard())
    await WarmupStates.WAITING_DURATION.set()

# Обработка выбора длительности
@dp.callback_query_handler(lambda c: c.data.startswith('dur_'), state=WarmupStates.WAITING_DURATION)
async def process_duration(callback_query: types.CallbackQuery, state: FSMContext):
    duration = int(callback_query.data.split('_')[1])
    data = await state.get_data()
    group_link = data['group_link']
    
    # Проверка дневного лимита
    allowed, used_hours = check_daily_limit(duration)
    if not allowed:
        await bot.send_message(
            callback_query.from_user.id,
            f"❌ Превышен дневной лимит прогрева!\n"
            f"Использовано часов сегодня: {used_hours}/{MAX_DAILY_HOURS}\n"
            f"Попробуйте завтра или выберите меньшую длительность."
        )
        await state.finish()
        return
    
    # Генерация уникальной сессии
    session_id = f"{callback_query.from_user.id}_{int(time.time())}"
    os.makedirs(f"sessions/{session_id}", exist_ok=True)
    
    # Генерация сообщений через DeepSeek
    total_messages = duration * MESSAGES_PER_HOUR
    await bot.send_message(callback_query.from_user.id, f"🧠 Генерация {total_messages} AI-сообщений...")
    
    try:
        messages = await generate_ai_messages(total_messages)
        
        # Сохранение сообщений в файл
        messages_file = f"sessions/{session_id}/messages.json"
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            
        # Запуск Node.js скрипта
        cmd = [
            "node", "whatsapp_sender.js",
            session_id,
            group_link,
            str(duration),
            messages_file
        ]
        
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Отправка QR-кода
        qr_path = f"sessions/{session_id}_qr.txt"
        await asyncio.sleep(3)  # Даем время на генерацию QR
        
        if os.path.exists(qr_path):
            with open(qr_path, 'r') as qr_file:
                qr_code = qr_file.read()
                await bot.send_message(
                    callback_query.from_user.id,
                    f"📲 Отсканируйте QR-код в WhatsApp:\n"
                    f"Настройки → Связанные устройства → Связать устройство\n\n"
                    f"`{qr_code}`",
                    parse_mode="Markdown"
                )
        else:
            await bot.send_message(callback_query.from_user.id, "⚠️ QR-код не сгенерирован, попробуйте снова")
        
        # Уведомление админу
        await bot.send_message(
            ADMIN_ID,
            f"🔥 Запущен прогрев: \n"
            f"Пользователь: @{callback_query.from_user.username}\n"
            f"Длительность: {duration} часов\n"
            f"Сообщений: {total_messages}\n"
            f"Использовано часов сегодня: {used_hours + duration}/{MAX_DAILY_HOURS}"
        )
        
    except Exception as e:
        await bot.send_message(callback_query.from_user.id, f"❌ Ошибка: {str(e)}")
    
    await state.finish()

if __name__ == '__main__':
    import time
    os.makedirs("sessions", exist_ok=True)
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)