import asyncio
import logging
from aiogram import Bot, Dispatcher, html
from aiogram.types import Message
from aiogram.filters import CommandStart
import aiohttp

# Bot va Binance sozlamalari
BOT_TOKEN = "8485772655:AAG2Ic-MJwayxUSJfHP6Otx4uD8ULdHFKH4"
BINANCE_URL = "https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT"

# Loglarni sozlash (Xatoliklarni ko'rish uchun)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# /start buyrug'i kelganda
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        f"Salom, {html.bold(message.from_user.full_name)}! \n"
        f"📈 Pocket Option Signal Botiga xush kelibsiz.\n\n"
        f"Bot fond bozorini tahlil qilishni boshladi. "
        f"Kuchli signallar bo'lishi bilan shu yerga yuboraman!"
    )

# Binance'dan narxni tekshirib turuvchi asinxron funksiya
async def check_market():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(BINANCE_URL) as response:
                    if response.status == 200:
                        data = await response.json()
                        current_price = float(data['price'])
                        
                        # LOG oynasida narxni ko'rib turish uchun
                        print(f"Hozirgi EUR/USD narxi: {current_price}")
                        
                        # TODO: Shu yerga RSI, Bollinger va EMA algoritmlarini qo'shamiz
                        # Agar signal to'g'ri kelsa, bot foydalanuvchiga xabar yuboradi
                        
            except Exception as e:
                print(f"Xatolik yuz berdi: {e}")
            
            # Har 5 soniyada bozorni tekshirish (Siz aytgan 5-6 soniyalik tezlik)
            await asyncio.sleep(5)

# Botni ishga tushirish
async def main():
    # Bozorni tekshirish funksiyasini orqa fonda (background) ishga tushiramiz
    asyncio.create_task(check_market())
    
    # Telegram botni yoqamiz
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
