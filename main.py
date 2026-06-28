import matplotlib
matplotlib.use('Agg') # WICHTIG: Damit der Server Bilder ohne Monitor rendert

import logging
import nest_asyncio
import os
import json
import urllib.request
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Nest_asyncio für die Bot-Stabilität
nest_asyncio.apply()
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------------------------------------------------------------------
# KONFIGURATION
# ---------------------------------------------------------------------------
ADMIN_ID = 8453096596
ALLOWED_USERS = set()
BOT_TOKEN = "8975995836:AAEhxOhCGXPG4mDWtLtN_7eFx7RrcTMcNJ8"

def has_access(user_id):
    return user_id in ALLOWED_USERS or user_id == ADMIN_ID or ADMIN_ID == 0

# ---------------------------------------------------------------------------
# CHART LOGIK
# ---------------------------------------------------------------------------
def fetch_live_chart_built_in(coin_name):
    symbol = f"{coin_name.upper()}USDT"
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=80"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
        
    extracted = [[pd.to_datetime(c[0], unit='ms'), float(c[1]), float(c[2]), float(c[3]), float(c[4])] for c in data]
    df = pd.DataFrame(extracted, columns=['timestamp', 'Open', 'High', 'Low', 'Close']).set_index('timestamp')
    
    colors = mpf.make_marketcolors(up='white', down='#0026ff', edge='inherit', wick='inherit')
    custom_style = mpf.make_mpf_style(marketcolors=colors, facecolor='black', figcolor='black', gridcolor='#1c1c1c', gridstyle='-', rc={'text.color': 'white', 'axes.labelcolor': 'gray', 'xtick.color': 'white', 'ytick.color': 'white'})
    
    out = f"chart_{coin_name}.png"
    fig, ax = mpf.plot(df, type='candle', style=custom_style, returnfig=True, figsize=(11, 5.5), datetime_format='%b %d, %H:%M')
    
    ax[0].set_ylabel('') 
    ax[0].set_title(f"{coin_name.upper()}/USDT - 1H", loc='left', color='white', fontsize=14, fontweight='bold', pad=10)
    ax[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.4f}"))
    
    plt.savefig(out, bbox_inches='tight', facecolor='black', dpi=100)
    plt.close()
    return out

# ---------------------------------------------------------------------------
# COMMANDS & HANDLER (gekürzt auf das Wesentliche)
# ---------------------------------------------------------------------------
async def handle_signal(update: Update, context: ContextTypes.DEFAULT_TYPE, is_long: bool):
    if not has_access(update.effective_user.id): return
    try:
        coin = context.args[0].upper()
        status = await update.message.reply_text(f"🔄 Generating chart...")
        path = fetch_live_chart_built_in(coin)
        with open(path, 'rb') as p:
            await update.message.reply_photo(photo=p, caption=f"📈 Chart for {coin}", parse_mode="Markdown")
        os.remove(path)
        await status.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def start_command(update, context):
    await update.message.reply_text("Bot active! Use /long or /short.")

# ---------------------------------------------------------------------------
# START
# ---------------------------------------------------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("long", lambda u, c: handle_signal(u, c, True)))
    app.add_handler(CommandHandler("short", lambda u, c: handle_signal(u, c, False)))
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
