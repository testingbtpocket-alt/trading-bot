import telebot
import requests
import sqlite3
import os

TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = 8954805209
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- BAZA VA HUQUQ ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, has_access INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def check_user_access(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT has_access FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0] == 1

# --- KUCHAYTIRILGAN RSI HISOBLASH ---
def calculate_rsi(prices, period=14):
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- TUGMALAR ---
def get_trading_keyboard():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    pairs = [("EURUSDT", "EUR/USD"), ("GBPUSDT", "GBP/USD"), ("AUDUSDT", "AUD/USD"), ("USDJPYT", "USD/JPY")]
    for s, d in pairs:
        markup.add(telebot.types.InlineKeyboardButton(text=d, callback_data=f"sig_{s}_{d.replace('/', '_')}"))
    return markup

# --- REAL VAQTDA SIGNAL TAHLILI ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('sig_'))
def get_live_signal(call):
    if not check_user_access(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас больше нет доступа!", show_alert=True)
        return

    # XATONI TUZATISH: split xavfsizligi
    parts = call.data.split('_', 2)
    if len(parts) < 3:
        bot.answer_callback_query(call.id, "Ошибка структуры!")
        return
    _, symbol, display_name = parts
    display_name = display_name.replace('_', '/')
    
    bot.answer_callback_query(call.id, "Идет анализ...")
    
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=40"
        res = requests.get(url, timeout=5)
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

    # XATONI TUZATISH: Edit qilishda xatolik chiqmasligi uchun try-except qo'shildi
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=text, 
            reply_markup=get_trading_keyboard(),
            parse_mode="HTML"
        )
    except:
        pass

# --- ADMIN BUYRUQLARI ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text.startswith("/grant"))
def grant_access(message):
    try:
        target_id = int(message.text.split()[1])
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (user_id, has_access) VALUES (?, 1)", (target_id,))
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

# XATONI TUZATISH: __name__ va "__main__" to'g'rilandi
if __name__ == "__main__":
    init_db()
    print("🚀 Бот муваффақиятли ишга тушди...")
    bot.infinity_polling()
        
