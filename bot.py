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

# --- SIGNAL LOGIKASI (TUZATILGAN) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('sig_'))
def get_live_signal(call):
    if not check_user_access(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Kirish huquqi yo'q!", show_alert=True)
        return

    parts = call.data.split('_', 2)
    _, symbol, display_name = parts
    display_name = display_name.replace('_', '/')
    
    bot.answer_callback_query(call.id, "Tahlil qilinyapti...")
    
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=40"
        res = requests.get(url, timeout=5).json()
        closes = [float(c[4]) for c in res]
        last_rsi = calculate_rsi(closes)
        
        # KUCHAYTIRILGAN SIGNAL MANTIG'I
        if last_rsi < 30:
            result = "🟢 KUCHLI CALL (Oversold)"
        elif last_rsi < 45:
            result = "🟢 Kichik CALL (Trendni kuzat)"
        elif last_rsi > 70:
            result = "🔴 KUCHLI PUT (Overbought)"
        elif last_rsi > 55:
            result = "🔴 Kichik PUT (Trendni kuzat)"
        else:
            result = "🟡 Neytral hudud: Bozor aniq emas"

        text = (f"📊 <b>{display_name}</b>\n"
                f"📈 RSI darajasi: {last_rsi:.2f}\n"
                f"🎯 Tavsiya: {result}\n\n"
                f"<i>Izoh: RSI {last_rsi:.2f} bo'yicha tahlil qilindi.</i>")
        
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=get_trading_keyboard())
    except Exception as e:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"❌ Xatolik yuz berdi: {e}")

# --- ADMIN BUYRUQLARI ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text.startswith('/'))
def admin_commands(message):
    parts = message.text.split()
    if len(parts) < 2: return
    cmd, target_id = parts[0], int(parts[1])
    access = 1 if cmd == '/grant' else 0
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, has_access) VALUES (?, ?)", (target_id, access))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ ID {target_id} uchun ruxsat {'berildi' if access==1 else 'olindi'}.")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Juftlikni tanlang:", reply_markup=get_trading_keyboard())

if __name__ == "__main__":
    init_db()
    print("🚀 Bot ishga tushdi!")
    bot.infinity_polling()
    
