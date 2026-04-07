import os
import telebot
from telebot import types
import sqlite3
import random
import time
import threading 
import requests
from datetime import datetime, timedelta
from flask import Flask 
# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN") 

WEATHER_API_KEY = "05e52fae7358456083721512426050"



bot = telebot.TeleBot(TOKEN)
BOT_NAME = "ирис"

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect("iris_final_v3.db", check_same_thread=False)
cursor = conn.cursor()

# 1. Сначала пытаемся создать таблицу с нужной колонкой (для новых баз)
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
               (user_id INTEGER PRIMARY KEY, name TEXT, rep INTEGER DEFAULT 100, 
                partner_id INTEGER DEFAULT 0, last_work TEXT, is_vip INTEGER DEFAULT 0)''')
conn.commit()

# 2. А ТЕПЕРЬ САМОЕ ВАЖНОЕ (для твоей текущей базы):
try:
    cursor.execute("ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0")
    conn.commit()
except:
    pass


# --- КЛАВИАТУРА ---
def main_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("👤 Профиль"), types.KeyboardButton("💰 Работа"))
    markup.add(types.KeyboardButton("🏆 ТОП"), types.KeyboardButton("📚 Помощь"))
    return markup
# --- СИСТЕМНЫЕ ФУНКЦИИ (ОБЯЗАТЕЛЬНО) ---

def get_user(user_id, name="Странник"):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        # Добавляем нового юзера (6 колонок: id, name, rep, partner, work, is_vip)
        cursor.execute("INSERT INTO users (user_id, name, last_work, is_vip) VALUES (?, ?, ?, ?)", 
                       (user_id, name, "2000-01-01 00:00:00", 0))
        conn.commit()
        return (user_id, name, 100, 0, "2000-01-01 00:00:00", 0)
    return user

def update_rep(user_id, amount):
    cursor.execute("UPDATE users SET rep = rep + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def is_admin(message):
    if message.chat.type == "private": return True
    try:
        status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return status in ['administrator', 'creator']
    except:
        return False

# --- ОСНОВНЫЕ КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def start(message):
    get_user(message.from_user.id, message.from_user.first_name)
    bot.send_message(message.chat.id, f"👑Игра началась. Я — Лелуш, твой гроссмейстер. Чтобы победить, нужно быть готовым к жертвам. Начнем партию?'.", reply_markup=main_kb())
@bot.message_handler(func=lambda m: m.text and m.text.lower() in ["помощь", "📚 помощь", "/help"])
def help_command(message):
    help_text = (
        "🎭 **ИНФОРМАЦИОННЫЙ ЦЕНТР ОРДЕНА**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👤 **АККАУНТ И СТАТЫ:**\n"
        "• `Профиль` — Твои ресурсы и влияние\n"
        "• `Ник [имя]` — Сменить позывной в системе\n"
        "• `🏆 ТОП` — Список самых богатых повстанцев\n\n"

        "🪷 **ЭКОНОМИКА (ЛОТОСЫ):**\n"
        "• `Работать` — Получить лотосы (раз в 5 мин)\n"
        "• `Передать [сумма]` — Отправить лотосы союзнику\n"
        "• `Купить ВИП` — Статус VIP за `5000` 🪷 (X2 доход)\n\n"

        "🎰 **ИГРЫ И РИСК:**\n"
        "• `Казино [сумма]` — Игра на удачу\n"
        "• `Казино все` — Рискнуть ВСЕМ балансом\n"
        "• `Дуэль` — (реплаем) Бой на `50` лотосов\n\n"

        "🎭 **РП И СОЦИАЛКА:**\n"
        "• `Обнять`, `кусь`, `ударить` — (реплаем)\n"
        "• `Брак` — (реплаем) Заключить союз\n\n"

        "🛡 **ПРАВОСУДИЕ (АДМИНЫ):**\n"
        "• `!бан`, `!мут [мин]`, `!размут` — (реплаем)\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👁 _«Мир нельзя изменить одними лишь словами.» — Лелуш_"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")


# --- ЭКОНОМИКА И ИГРЫ ---

@bot.message_handler(func=lambda m: m.text in ["👤 Профиль", "профиль"])
def profile(message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    partner = "Нет" if u[3] == 0 else f"ID {u[3]}"
    bot.reply_to(message, f"👤 **Имя:** {u[1]}\n🪷 **Баланс:** {u[2]} лотосов\n💍 **Брак:** {partner}", parse_mode="Markdown")
@bot.message_handler(func=lambda m: m.text in ["💰 Работа", "работа", "Работать"])
def work(message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    last_w = datetime.strptime(u[4], "%Y-%m-%d %H:%M:%S")
    
    if datetime.now() - last_w < timedelta(minutes=5):
        wait = (timedelta(minutes=5) - (datetime.now() - last_w)).seconds
        return bot.reply_to(message, f"⏳ Рано! Отдохни {wait} сек.")
    
    reward = random.randint(30, 150)
    
    # ПРОВЕРКА НА VIP (индекс 5)
    is_vip = u[5] if len(u) > 5 else 0
    
    if is_vip == 1:
        reward *= 2 # Удваиваем награду
        text = f"⚙️ **VIP-БОНУС АКТИВИРОВАН!**\nВы заработали: `{reward}` 🪷"
    else:
        text = f"⚒ Ты отработал смену! Получено: {reward} 🪷"
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE users SET rep = rep + ?, last_work = ? WHERE user_id = ?", (reward, now, u[0]))
    conn.commit()
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("казино"))
def casino(message):
    args = message.text.split()
    u = get_user(message.from_user.id)
    if len(args) < 2: return bot.reply_to(message, "🎰 Ставка? (число или 'все')")
    
    bet = u[2] if args[1].lower() in ["все", "all", "алл"] else (int(args[1]) if args[1].isdigit() else 0)
    if bet <= 0 or bet > u[2]: return bot.reply_to(message, "❌ Ошибка ставки!")

    if random.choice([True, False]):
        update_rep(u[0], bet)
        bot.reply_to(message, f"📈 **ПОБЕДА!** +{bet} 🪷\nБаланс: {u[2]+bet}")
    else:
        update_rep(u[0], -bet)
        bot.reply_to(message, f"📉 **ПРОИГРЫШ!** -{bet} 🪷\nБаланс: {u[2]-bet}")

@bot.message_handler(func=lambda m: m.text == "🏆 ТОП")
def top(message):
    cursor.execute("SELECT name, rep FROM users ORDER BY rep DESC LIMIT 10")
    res = cursor.fetchall()
    top_msg = "🏆 **СПИСОК ЛИДЕРОВ:**\n\n"
    for i, row in enumerate(res, 1):
        top_msg += f"{i}. {row[0]} — {row[1]} 🪷\n"
    bot.send_message(message.chat.id, top_msg, parse_mode="Markdown")

# --- РП И БРАКИ ---

@bot.message_handler(func=lambda m: m.text and m.text.lower() in ["обнять", "кусь", "ударить", "погладить"])
def rp_actions(message):
    if not message.reply_to_message: return
    actions = {"обнять": "обнял(а)", "кусь": "сделал(а) кусь", "ударить": "ударил(а)", "погладить": "погладил(а)"}
    act = actions[message.text.lower()]
    bot.send_message(message.chat.id, f"🎭 {message.from_user.first_name} {act} {message.reply_to_message.from_user.first_name}")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "брак")
def marriage(message):
    if not message.reply_to_message: return bot.reply_to(message, "Ответь тому, с кем хочешь брак!")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Да", callback_data=f"m_y_{message.from_user.id}_{message.reply_to_message.from_user.id}"),
           types.InlineKeyboardButton("❌ Нет", callback_data="m_n"))
    bot.send_message(message.chat.id, f"💍 {message.reply_to_message.from_user.first_name}, ты согласен(а) на брак с {message.from_user.first_name}?", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("m_"))
def marriage_cb(call):
    if call.data == "m_n": return bot.edit_message_text("💔 Отказ...", call.message.chat.id, call.message.message_id)
    _, _, u1, u2 = call.data.split("_")
    if call.from_user.id != int(u2): return bot.answer_callback_query(call.id, "Не тебе!")
    cursor.execute("UPDATE users SET partner_id = ? WHERE user_id = ?", (u2, u1))
    cursor.execute("UPDATE users SET partner_id = ? WHERE user_id = ?", (u1, u2))
    conn.commit()
    bot.edit_message_text("🎉 Горько! Свадьба состоялась! 💍", call.message.chat.id, call.message.message_id)

# --- МОДЕРАЦИЯ ---

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("!бан"))
def ban_user(message):
    if is_admin(message) and message.reply_to_message:
        bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, "✈️ Бан выдан!")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("!мут"))
def mute_user(message):
    if is_admin(message) and message.reply_to_message:
        args = message.text.split()
        tm = int(args[1]) if len(args) > 1 and args[1].isdigit() else 15
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=int(time.time())+tm*60)
        bot.reply_to(message, f"🔇 Мут на {tm} минут.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "!размут")
def unmute_user(message):
    if is_admin(message) and message.reply_to_message:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        bot.reply_to(message, "🔊 Говори!")
# --- ЗАПУСК ---
if __name__ == "__main__":
    # 1. Запускаем Flask для Render в фоне (обязательно daemon=True)
    threading.Thread(target=run_flask, daemon=True).start()
    
    # 2. Даем серверу 2 секунды, чтобы он «зацепился» за порт
    time.sleep(2)
    
    # 3. Запуск самого бота через infinity_polling
    print("Бот Лелуш запущен!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
  

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "пинг")
def ping_pong(message):
    bot.reply_to(message, "🏓 Понг!")
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("погода"))
def get_weather(message):
    args = message.text.split()
    
    if len(args) < 2:
        return bot.reply_to(message, "📍 Напиши город, например: `погода Днепр`", parse_mode="Markdown")
    
    city = " ".join(args[1:]) # Берем всё, что идет после слова "погода"
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}&lang=ru"
    
    try:
        response = requests.get(url).json()
        
        if "error" in response:
            return bot.reply_to(message, f"❌ Город '{city}' не найден.")
        
        # Данные из ответа API
        temp = response['current']['temp_c']
        condition = response['current']['condition']['text']
        feels_like = response['current']['feelslike_c']
        wind = response['current']['wind_kph']
        humidity = response['current']['humidity']
        city_name = response['location']['name']
        
        weather_text = (
            f"🌍 **Погода в {city_name}**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🌡 Температура: `{temp}°C`\n"
            f"🤔 Ощущается как: `{feels_like}°C`\n"
            f"☁️ Состояние: {condition}\n"
            f"💨 Ветер: `{wind} км/ч`\n"
            f"💧 Влажность: `{humidity}%`"
        )
        
        bot.reply_to(message, weather_text, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, "⚠️ Ошибка при получении погоды. Попробуй позже.")
        print(f"Weather Error: {e}")
# --- ОТВЕТ НА ИМЯ ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() in ["лелуш", "lelouch", "ирис"])
def answer_on_name(message):
    # Список возможных ответов
    responses = [
        "Что надо?", 
        "Когда ты уже провалишься...", 
        "Слушаю. Только быстро.", 
        "Опять ты? Я занят.", 
        "Лелуш тут", 
        "Чего желаешь?",
        "Ну и что тебе на этот раз?"
    ]
    # Выбираем случайный ответ и отправляем реплаем
    bot.reply_to(message, random.choice(responses))
# --- КАЛЬКУЛЯТОР ---

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith(("вычисли", "реши", "calc")))
def calculate(message):
    try:
        # Убираем само слово "вычисли" и оставляем только выражение
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            return bot.reply_to(message, "🔢 Напиши выражение, например: `вычисли 2 + 2 * 5`", parse_mode="Markdown")
        
        expression = parts[1].replace(":", "/").replace(",", ".") # Небольшие исправления для удобства
        
        # Список разрешенных символов для безопасности (цифры и знаки)
        allowed_chars = "0123456789+-*/(). "
        if not all(char in allowed_chars for char in expression):
            return bot.reply_to(message, "❌ Ошибка: Использованы недопустимые символы. Только цифры и `+ - * /`.")

        # Вычисляем результат
        result = eval(expression)
        
        # Красивый вывод
        bot.reply_to(message, f"📊 **Результат:**\n`{expression} = {result}`", parse_mode="Markdown")
        
    except ZeroDivisionError:
        bot.reply_to(message, "❌ На ноль делить нельзя!")
    except Exception as e:
        bot.reply_to(message, "❌ Ошибка в выражении. Проверь правильность написания.")
# --- СИСТЕМА ПЕРЕВОДОВ С КОМИССИЕЙ ---

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("передать"))
def transfer_money(message):
    # 1. Проверка на реплай
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Чтобы передать лотосы, ответь этой командой на сообщение получателя!")

    # 2. Нельзя самому себе
    if message.from_user.id == message.reply_to_message.from_user.id:
        return bot.reply_to(message, "🤔 Самому себе передавать нельзя, это же просто перекладывание из кармана в карман.")

    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "💰 Укажи сумму. Например: `передать 100` \n*(Комиссия за перевод — 5%)*", parse_mode="Markdown")

    try:
        amount = int(args[1])
        if amount <= 0:
            return bot.reply_to(message, "❌ Сумма должна быть больше нуля!")
    except ValueError:
        return bot.reply_to(message, "❌ Сумма должна быть целым числом!")

    # 3. Получаем данные игроков
    sender = get_user(message.from_user.id, message.from_user.first_name)
    receiver = get_user(message.reply_to_message.from_user.id, message.reply_to_message.from_user.first_name)

    # 4. Проверка баланса отправителя
    if sender[2] < amount:
        return bot.reply_to(message, f"📉 Недостаточно лотосов! У тебя всего {sender[2]} 🪷")

    # 5. Считаем комиссию (5%)
    fee = int(amount * 0.05)
    final_amount = amount - fee

    # 6. Проводим транзакцию
    update_rep(sender[0], -amount)      # Списываем полную сумму
    update_rep(receiver[0], final_amount) # Начисляем сумму за вычетом комиссии

    bot.send_message(
        message.chat.id, 
        f"💸 **Успешный перевод!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 **Отправитель:** {sender[1]}\n"
        f"👤 **Получатель:** {receiver[1]}\n"
        f"💰 **Сумма:** `{amount}` 🪷\n"
        f"📉 **Комиссия (5%):** `{fee}` 🪷\n"
        f"🎁 **Пришло на счет:** `{final_amount}` 🪷",
        parse_mode="Markdown"
    )
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "купить вип")
def buy_vip(message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    
    balance = user[2] # В твоей БД это колонка rep
    # Проверяем VIP статус. В твоей таблице это будет 6-й элемент (индекс 5)
    try:
        is_vip = user[5] 
    except IndexError:
        is_vip = 0 # На случай, если колонка еще не создалась
    
    if is_vip == 1:
        bot.reply_to(message, "👁 У вас уже есть статус VIP.")
        return

    if balance >= 5000:
        # ИСПРАВЛЕНО: списываем из rep, ставим is_vip = 1
        cursor.execute("UPDATE users SET rep = rep - 5000, is_vip = 1 WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        bot.reply_to(message, "👑 **Контракт заключен!**\nТеперь вы обладаете статусом VIP.")
    else:
        bot.reply_to(message, f"❌ Недостаточно лотосов. Нужно `5000` 🪷, у вас `{balance}`.")

        bot.reply_to(message, f"❌ Недостаточно средств. Нужно `5000` 🪷, а у вас лишь `{balance}`.")
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("выдать "))
def give_money_admin(message):
    # Проверка на админа через твою готовую функцию is_admin
    if not is_admin(message):
        bot.reply_to(message, "👁 Эту силу может использовать только тот, кто готов нести бремя власти.")
        return

    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Команда должна быть ответом на сообщение!")
        return

    try:
        amount = int(message.text.split()[1])
        target_id = message.reply_to_message.from_user.id
        
        # ИСПРАВЛЕНО: используем rep вместо balance
        cursor.execute("UPDATE users SET rep = rep + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()

        bot.reply_to(message, f"🎭 **Приказ Лелуша исполнен!**\nСчет пополнен на `{amount}` 🪷.")
    except:
        bot.reply_to(message, "⚠️ Используйте формат: `выдать [сумма]`")
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("ник "))
def change_name(message):
    new_name = message.text[4:].strip() # Отрезаем слово "ник "
    if len(new_name) > 20:
        return bot.reply_to(message, "⚠️ Позывной слишком длинный (макс. 20 символов).")
    if len(new_name) < 2:
        return bot.reply_to(message, "⚠️ Позывной слишком короткий.")

    user_id = message.from_user.id
    cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
    conn.commit()
    
    bot.reply_to(message, f"🎭 **Приказ принят.**\nВаш новый позывной в системе: `{new_name}`", parse_mode="Markdown")
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "дуэль")
def duel(message):
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Чтобы вызвать на дуэль, ответь этой командой на сообщение противника!")

    challenger_id = message.from_user.id
    opponent_id = message.reply_to_message.from_user.id

    if challenger_id == opponent_id:
        return bot.reply_to(message, "🎭 Лелуш не одобряет попытки застрелить собственное отражение.")

    # Получаем данные игроков
    p1 = get_user(challenger_id, message.from_user.first_name)
    p2 = get_user(opponent_id, message.reply_to_message.from_user.id)

    bet = 50 # Ставка дуэли

    if p1[2] < bet:
        return bot.reply_to(message, f"📉 У вас недостаточно лотосов для вызова (нужно {bet} 🪷).")
    if p2[2] < bet:
        return bot.reply_to(message, f"❌ У противника недостаточно ресурсов для честного боя.")

    # Выбираем победителя
    winner, loser = random.choice([(p1, p2), (p2, p1)])

    # Обновляем базу
    update_rep(winner[0], bet)
    update_rep(loser[0], -bet)

    result_text = (
        f"⚔️ **ДУЭЛЬ СОСТОЯЛАСЬ!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏆 Победитель: {winner[1]} (+{bet} 🪷)\n"
        f"💀 Проигравший: {loser[1]} (-{bet} 🪷)\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👁 _Судьба была на стороне сильнейшего._"
    )
    bot.send_message(message.chat.id, result_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "слоты")
def slots_game(message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    bet = 50 # Ставка на один прокрут
    
    if u[2] < bet:
        return bot.reply_to(message, f"📉 Ставка — `{bet}` 🪷. У вас не хватает.")

    # Списываем ставку сразу
    update_rep(u[0], -bet)
    
    # Отправляем кубик со слотами
    msg = bot.send_dice(message.chat.id, emoji='🎰')
    value = msg.dice.value # Значение от 1 до 64
    
    # В Telegram слоты работают так: 
    # 1, 22, 43, 64 — это три одинаковых символа (джекпот)
    # Остальные значения — разные комбинации.
    
    time.sleep(2) # Пауза, чтобы игрок увидел крутящиеся барабаны
    
    if value in [1, 22, 43, 64]:
        win = 1000 # Большой выигрыш
        update_rep(u[0], win)
        bot.reply_to(message, f"💎 **ДЖЕКПОТ!**\nВы выиграли `{win}` 🪷!")
    elif value in [16, 32, 48]: # Две одинаковых (условно)
        win = 150
        update_rep(u[0], win)
        bot.reply_to(message, f"💰 **НЕПЛОХО!**\nВыигрыш: `{win}` 🪷!")
    else:
        bot.reply_to(message, "☁️ Удача сегодня не на вашей сторонне. Попробуйте снова!")
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("сейф"))
def safe_game(message):
    # 1. Получаем данные игрока
    u = get_user(message.from_user.id, message.from_user.first_name)
    cost = 100 
    
    # 2. Проверяем баланс (u[2] — это твоя колонка rep)
    if u[2] < cost:
        return bot.reply_to(message, f"📉 Для взлома сейфа нужно `{cost}` 🪷. У вас всего `{u[2]}`.")

    # 3. Обрабатываем ввод числа
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "🔢 Укажите код! Пример: `сейф 5` (от 1 до 10)")

    try:
        guess = int(args[1])
        if not (1 <= guess <= 10):
            return bot.reply_to(message, "⚠️ Код должен быть в диапазоне от 1 до 10!")
    except ValueError:
        return bot.reply_to(message, "❌ Введите число, а не текст!")

    # 4. Логика выигрыша
    winning_code = random.randint(1, 10)
    
    if guess == winning_code:
        prize = cost * 10
        # Обновляем через твою функцию update_rep
        update_rep(u[0], prize - cost) 
        bot.reply_to(message, f"🔓 **СЕЙФ ОТКРЫТ!**\nВы угадали код `{winning_code}` и получили `{prize}` 🪷!")
    else:
        update_rep(u[0], -cost)
        bot.reply_to(message, f"🔒 **НЕВЕРНО!**\nКод был `{winning_code}`. Вы потеряли `{cost}` 🪷.\nПопробуете еще раз?")


print("Бот запущен! Проверь Telegram.")
bot.infinity_polling()
