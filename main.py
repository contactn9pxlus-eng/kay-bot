import logging
import nest_asyncio
import os
import json
import urllib.request
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

nest_asyncio.apply()
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Token hier eintragen oder besser via Railway Variables!
TELEGRAM_TOKEN = "8975995836:AAEhxOhCGXPG4mDWtLtN_7eFx7RrcTMcNJ8"
ADMIN_ID = 8453096596
ALLOWED_USERS = {ADMIN_ID}

def has_access(user_id):
    return user_id in ALLOWED_USERS

# Daten von Binance abrufen
def fetch_live_chart(coin_name):
    symbol = f"{coin_name.upper()}USDT"
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=80"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
    
    # Daten umwandeln
    extracted = [[pd.to_datetime(c[0], unit='ms'), float(c[1]), float(c[2]), float(c[3]), float(c[4])] for c in data]
    df = pd.DataFrame(extracted, columns=['timestamp', 'Open', 'High', 'Low', 'Close']).set_index('timestamp')
    
    # Chart erstellen
    colors = mpf.make_marketcolors(up='white', down='#0026ff', edge='inherit', wick='inherit')
    style = mpf.make_mpf_style(marketcolors=colors, facecolor='black', figcolor='black', gridcolor='#1c1c1c')
    
    out = f"chart_{coin_name}.png"
    mpf.plot(df, type='candle', style=style, savefig=out, figsize=(11, 5.5), title=f"{coin_name.upper()}/USDT - 1H")
    return out

# Telegram Handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot ist bereit! Nutze /long oder /short.")

async def handle_signal(update: Update, context: ContextTypes.DEFAULT_TYPE, is_long: bool):
    if not has_access(update.effective_user.id):
        return
    
    coin = context.args[0].upper() if context.args else "BTC"
    
    try:
        status = await update.message.reply_text(f"Lade aktuelle Daten für {coin}...")
        path = fetch_live_chart(coin)
        with open(path, 'rb') as p:
            await update.message.reply_photo(photo=p, caption=f"{'LONG' if is_long else 'SHORT'} Signal für {coin}")
        os.remove(path)
        await status.delete()
    except Exception as e:
        await update.message.reply_text(f"Fehler beim Abrufen der Daten: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("long", lambda u, c: handle_signal(u, c, True)))
    app.add_handler(CommandHandler("short", lambda u, c: handle_signal(u, c, False)))
    
    print("Bot läuft!")
    app.run_polling()

if __name__ == '__main__':
    main()
