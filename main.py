import matplotlib
matplotlib.use('Agg')

import sys, subprocess, logging, os, json, urllib.request
import nest_asyncio
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Installieren beim Start
subprocess.check_call([sys.executable, "-m", "pip", "install", "mplfinance", "matplotlib", "pandas", "numpy", "python-telegram-bot", "ccxt"])

nest_asyncio.apply()
logging.basicConfig(level=logging.INFO)

def fetch_live_chart(coin_name):
    # Live Daten von Binance
    url = f"https://api.binance.com/api/v3/klines?symbol={coin_name.upper()}USDT&interval=1h&limit=80"
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})) as res:
        data = json.loads(res.read().decode())
    df = pd.DataFrame([[pd.to_datetime(c[0], unit='ms'), float(c[1]), float(c[2]), float(c[3]), float(c[4])] for c in data], 
                      columns=['timestamp', 'Open', 'High', 'Low', 'Close']).set_index('timestamp')
    
    # Design exakt wie in deinem Screenshot
    colors = mpf.make_marketcolors(up='white', down='#0026ff', edge='inherit', wick='inherit')
    style = mpf.make_mpf_style(marketcolors=colors, facecolor='black', figcolor='black', gridcolor='#1c1c1c')
    
    filename = f"chart_{coin_name}.png"
    fig, ax = mpf.plot(df, type='candle', style=style, returnfig=True, figsize=(11, 5.5))
    ax[0].set_title(f"{coin_name.upper()}/USDT - 1H", loc='left', color='white', fontsize=14, fontweight='bold', pad=10)
    plt.savefig(filename, bbox_inches='tight', facecolor='black', dpi=100)
    plt.close()
    return filename

async def handle_signal(update: Update, context: ContextTypes.DEFAULT_TYPE, is_long: bool):
    args = context.args
    coin = args[0].upper()
    entry = args[1]
    tp = args[args.index("-tp") + 1] if "-tp" in args else "N/A"
    sl = args[args.index("-sl") + 1] if "-sl" in args else "N/A"
    lev = args[args.index("-s") + 1] if "-s" in args else "20-50"

    caption = (f"{'*📈 LONG*' if is_long else '*📉 SHORT*'} - ${coin}\n\n"
               f"🏷 *Entry Price:* ${entry}\n\n✅ *TP1:* ${tp}\n\n❌ *SL:* ${sl}\n\n"
               f"_(Suggested Lev. {lev}x)_\n_(Suggested Margin N/A%)_")

    status = await update.message.reply_text("🔄 Generating chart...")
    try:
        path = fetch_live_chart(coin)
        with open(path, 'rb') as p:
            await update.message.reply_photo(photo=p, caption=caption, parse_mode="Markdown")
        os.remove(path)
    except Exception as e:
        await update.message.reply_text(f"❌ System Fehler: {e}")
    await status.delete()

def main():
    app = Application.builder().token("8975995836:AAEhxOhCGXPG4mDWtLtN_7eFx7RrcTMcNJ8").build()
    app.add_handler(CommandHandler("long", lambda u, c: handle_signal(u, c, True)))
    app.add_handler(CommandHandler("short", lambda u, c: handle_signal(u, c, False)))
    app.run_polling()

if __name__ == '__main__':
    main()
