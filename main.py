import matplotlib
matplotlib.use('Agg') # WICHTIG für den Server

import sys
import subprocess
import nest_asyncio
nest_asyncio.apply()

# Installation der Abhängigkeiten
subprocess.check_call([sys.executable, "-m", "pip", "install", "mplfinance", "matplotlib", "pandas", "numpy", "python-telegram-bot", "ccxt"])

import logging
import os
import json
import urllib.request
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------------------------------------------------------------------
# CHART ENGINE (Live-Daten)
# ---------------------------------------------------------------------------
def fetch_live_chart(coin_name):
    symbol = f"{coin_name.upper()}USDT"
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=80"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
    
    extracted = [[pd.to_datetime(c[0], unit='ms'), float(c[1]), float(c[2]), float(c[3]), float(c[4])] for c in data]
    df = pd.DataFrame(extracted, columns=['timestamp', 'Open', 'High', 'Low', 'Close']).set_index('timestamp')
    
    colors = mpf.make_marketcolors(up='white', down='#0026ff', edge='inherit', wick='inherit')
    custom_style = mpf.make_mpf_style(marketcolors=colors, facecolor='black', figcolor='black', gridcolor='#1c1c1c', rc={'text.color': 'white', 'xtick.color': 'white', 'ytick.color': 'white'})
    
    out = f"chart_{coin_name}.png"
    fig, ax = mpf.plot(df, type='candle', style=custom_style, returnfig=True, figsize=(11, 5.5))
    ax[0].set_title(f"{coin_name.upper()}/USDT - 1H", loc='left', color='white', fontsize=14, fontweight='bold', pad=10)
    plt.savefig(out, bbox_inches='tight', facecolor='black', dpi=100)
    plt.close()
    return out

# ---------------------------------------------------------------------------
# SIGNAL LOGIK (für LONG und SHORT)
# ---------------------------------------------------------------------------
async def handle_signal(update: Update, context: ContextTypes.DEFAULT_TYPE, is_long: bool):
    args = context.args
    if not args: return
    
    coin = args[0].upper()
    entry = args[1]
    
    # Werte aus args extrahieren
    tp = args[args.index("-tp") + 1] if "-tp" in args else "N/A"
    sl = args[args.index("-sl") + 1] if "-sl" in args else "N/A"
    lev = args[args.index("-s") + 1] if "-s" in args else "N/A"

    caption = (
        f"{'📈 LONG' if is_long else '📉 SHORT'} - ${coin}\n\n"
        f"🏷 *Entry Price:* ${entry}\n\n"
        f"✅ *TP1:* ${tp}\n\n"
        f"❌ *SL:* ${sl}\n\n"
        f"(Suggested Lev. {lev}x)\n"
        f"(Suggested Margin N/A%)"
    )

    status = await update.message.reply_text(f"🔄 Generating chart...")
    try:
        path = fetch_live_chart(coin)
        with open(path, 'rb') as p:
            await update.message.reply_photo(photo=p, caption=caption, parse_mode="Markdown")
        os.remove(path)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    await status.delete()

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    app = Application.builder().token("8975995836:AAEhxOhCGXPG4mDWtLtN_7eFx7RrcTMcNJ8").build()
    app.add_handler(CommandHandler("long", lambda u, c: handle_signal(u, c, True)))
    app.add_handler(CommandHandler("short", lambda u, c: handle_signal(u, c, False)))
    print("Bot is ready!")
    app.run_polling()

if __name__ == '__main__':
    main()
