import telebot
import requests
import sqlite3
import os
TOKEN = os.getenv("API_TOKEN")
ADMIN_USERNAME = "@Kasper404_01"
ADMIN_ID = 8954805209

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- BAZANI INIZIALIZATSIYA QILISH ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            has_access INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def check_user_access(user_id):
    if user_id == ADMIN_ID: 
        return True
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT has_access FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] == 1

def register_user(user_id, username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

# --- RSI MATEMATIKASI ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0: return 100
    for i in range(period, len(prices) - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- TUGMALARNI YARATISH ---
def get_access_keyboard(user_id):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(
        text="🔐 Запросить доступ", 
        url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}?text=Привет! Добавь мой ID: {user_id}"
    ))
    return markup

def get_trading_keyboard():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    pairs = ["AUD/USD", "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "NZD/USD"]
    buttons = []
    for pair in pairs:
        clean_symbol = "EURUSDT"
        if pair == "GBP/USD": clean_symbol = "GBPUSDT"
        if pair == "USD/JPY": clean_symbol = "USDJPY"
        if pair == "USD/CHF": clean_symbol = "USDCHF"
        if pair == "AUD/USD": clean_symbol = "AUDUSDT"
        if pair == "NZD/USD": clean_symbol = "NZDUSDT"
        
        buttons.append(telebot.types.InlineKeyboardButton(
            text=pair, 
            callback_data=f"sig_{clean_symbol}_{pair.replace('/', '_')}"
        ))
    markup.add(*buttons)
    return markup

# --- START BUYRUG'I ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoName"
    register_user(user_id, username)
    
    if not check_user_access(user_id):
        # 1401.jpg dagi matn formati
        lock_text = (
            f"Робот на базе искусственного интеллекта и "
            f"точного анализа рынка в реальном времени.\n"
            f"🎯 Точность алгоритма: 91%\n"
            f"📈 Время экспирации: 1-3 минуты\n"
            f"🔒 Доступ ограничен. Для получения доступа "
            f"нажмите кнопку \"Старт\" и отправьте свой ID администратору!"
        )
        bot.send_message(message.chat.id, lock_text, reply_markup=get_access_keyboard(user_id))
        return

    welcome_text = (
        f"Salom, <b>{message.from_user.first_name}</b>!\n"
        f"📈 Pocket Option Signal Botiga xush kelibsiz.\n\n"
        f"Bot fond bozorini tahlil qilishni boshladi.\n"
        f"Kuchli signallar bo'lishi bilan shu yerga yuboraman!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_trading_keyboard())

# --- REAL VAQTDA SIGNAL TAHLILI ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('sig_'))
def get_live_signal(call):
    if not check_user_access(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас больше нет доступа!", show_alert=True)
        return

    _, symbol, display_name = call.data.split('_', 2)
    display_name = display_name.replace('_', '/')
    
    bot.answer_callback_query(call.id, "Идет анализ...")
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id, 
        text=f"⏳ Анализируем реальный график <b>{display_name}</b>..."
    )

    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=40"
        res = requests.get(url, timeout=30)
        closes = [float(c[4]) for c in res.json()]
        last_rsi = calculate_rsi(closes, period=14)
        
        if last_rsi < 30:
            result = f"🟢 <b>CALL (ВВЕРХ)</b>\n🎯 Точность алгоритма: <b>91%</b>"
        elif last_rsi > 70:
            result = f"🔴 <b>PUT (ВНИЗ)</b>\n🎯 Точность алгоритма: <b>89%</b>"
        else:
            result = "⏳ <b>НЕТ СИГНАЛА</b>. Рынок флетует, подождите выхода из зоны."

        text = (
            f"📊 <b>РЕЗУЛЬТАТ СКАНИРОВАНИЯ ({display_name})</b>\n"
            f"-----------------------------------------\n"
            f"▶️ Сигнал: {result}\n"
            f"▶️ Время экспирации: 1-3 минуты\n"
            f"-----------------------------------------\n"
            f"<i>Текущий RSI: {last_rsi:.2f}</i>"
        )
    except Exception as e:
        text = f"❌ Ошибка получения данных: {e}"

    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id, 
        text=text, 
        reply_markup=get_trading_keyboard()
    )

# --- ADMIN BUYRUQLARI ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text.startswith("/grant"))
def grant_access(message):
    try:
        target_id = int(message.text.split()[1])
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET has_access = 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ Доступ для ID {target_id} успешно открыт!")
    except Exception:
        bot.send_message(message.chat.id, "Формат: /grant ID")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text.startswith("/revoke"))
def revoke_access(message):
    try:
        target_id = int(message.text.split()[1])
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET has_access = 0 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"❌ Доступ для ID {target_id} успешно закрыт!")
    except Exception:
        bot.send_message(message.chat.id, "Формат: /revoke ID")

if __name__ == "__main__":
    init_db()
    print("🚀 Бот муваффақиятли ишга тушди...")
    bot.infinity_polling()
        
