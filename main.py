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

nest_asyncio.apply()
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------------------------------------------------------------------
# ACCESS CONTROL (Automatically sets the first person who types /start as Admin)
# ---------------------------------------------------------------------------
ADMIN_ID = 8453096596
ALLOWED_USERS = set()

def has_access(user_id):
    return user_id in ALLOWED_USERS or user_id == ADMIN_ID or ADMIN_ID == 0

# ---------------------------------------------------------------------------
# CHART ENGINE
# ---------------------------------------------------------------------------
def draw_pure_matplotlib_chart(coin_name):
    np.random.seed(1337)
    periods = 60
    prices = 0.085 + 0.01 * np.cumsum(np.random.randn(periods))
    prices = np.clip(prices, 0.06, 0.12)
    df = pd.DataFrame(index=range(periods))
    df['Close'] = prices
    df['Open'] = prices + np.random.uniform(-0.003, 0.003, periods)
    df['High'] = df[['Open', 'Close']].max(axis=1) + np.random.uniform(0, 0.002, periods)
    df['Low'] = df[['Open', 'Close']].min(axis=1) - np.random.uniform(0, 0.002, periods)
    
    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')
    ax.grid(color='#1c1c1c', linestyle='-', linewidth=1)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('gray')
    ax.spines['bottom'].set_color('gray')
    ax.tick_params(colors='white', labelsize=10)
    
    for i in range(periods):
        open_p, close_p = df['Open'].iloc[i], df['Close'].iloc[i]
        high_p, low_p = df['High'].iloc[i], df['Low'].iloc[i]
        color = 'white' if close_p >= open_p else '#0026ff'
        ax.plot([i, i], [low_p, high_p], color=color, linewidth=1)
        ax.fill_between([i-0.3, i+0.3], open_p, close_p, color=color, edgecolor=color)

    ax.text(0.01, 1.05, f"{coin_name.upper()}/USDT - 1H", transform=ax.transAxes, color='white', fontsize=14, fontweight='bold', ha='left')
    ax.text(df['High'].idxmax(), df['High'].max() + 0.002, "0.10", color='#ff0000', fontsize=11, fontweight='bold', ha='center', va='bottom')
    ax.text(df['Low'].idxmin(), df['Low'].min() - 0.002, "0.07", color='#00ff22', fontsize=11, fontweight='bold', ha='center', va='top')
    ax.set_xticks([]) 
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.4f}"))
    out = f"chart_{coin_name}.png"
    plt.savefig(out, bbox_inches='tight', facecolor='black', dpi=100)
    plt.close()
    return out

def fetch_live_chart_built_in(coin_name):
    symbol = f"{coin_name.upper()}USDT"
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=80"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
        extracted = [[pd.to_datetime(c[0], unit='ms'), float(c[1]), float(c[2]), float(c[3]), float(c[4])] for c in data]
        df = pd.DataFrame(extracted, columns=['timestamp', 'Open', 'High', 'Low', 'Close']).set_index('timestamp')
        colors = mpf.make_marketcolors(up='white', down='#0026ff', edge='inherit', wick='inherit')
        custom_style = mpf.make_mpf_style(marketcolors=colors, facecolor='black', figcolor='black', gridcolor='#1c1c1c', gridstyle='-', rc={'text.color': 'white', 'axes.labelcolor': 'gray', 'xtick.color': 'white', 'ytick.color': 'white'})
        
        # Plot erstellen
        fig, ax = mpf.plot(df, type='candle', style=custom_style, returnfig=True, figsize=(11, 5.5), datetime_format='%b %d, %H:%M')
        
        # HIER wird das "Price" entfernt:
        ax[0].set_ylabel('') 
        
        ax[0].set_title(f"{coin_name.upper()}/USDT - 1H", loc='left', color='white', fontsize=14, fontweight='bold', pad=10)
        ax[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.4f}"))
        out = f"chart_{coin_name}.png"
        plt.savefig(out, bbox_inches='tight', facecolor='black', dpi=100)
        plt.close()
        return out
    except Exception:
        return draw_pure_matplotlib_chart(coin_name)

        
# ---------------------------------------------------------------------------
# MENUS & BUTTONS (ENGLISH)
# ---------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user_id = update.effective_user.id
    
    # First person to message the bot becomes Owner/Admin
    if ADMIN_ID == 0:
        ADMIN_ID = user_id
        ALLOWED_USERS.add(user_id)
        logging.info(f"Main Admin successfully registered: {user_id}")

    if not has_access(user_id):
        await update.message.reply_text("⛔ *Access Denied.* You are not authorized to use this bot.", parse_mode="Markdown")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Chat CMDs", callback_data='chat_cmds')],
        [InlineKeyboardButton("⚙️ Other CMDs (Access)", callback_data='other_cmds')]
    ]
    await update.message.reply_text(
        "👋 *Welcome to the Control Center.*\n\nSelect a category from the buttons below:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def button_tap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not has_access(user_id):
        await query.edit_message_text("⛔ Access Denied.")
        return

    if query.data == 'chat_cmds':
        text = (
            "📋 *Available Chart Commands:*\n\n"
            "🟢 *Create LONG Signal:*\n"
            "`/long Token entry 0.1000 -tp 0.1200 -sl 0.0700 -s 15 5`\n\n"
            "🔴 *Create SHORT Signal:*\n"
            "`/short Token entry 0.1000 -tp 0.0800 -sl 0.1200 -s 15 5`\n\n"
            "_Tip: Long-press the code template to quickly copy it on your phone._"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]), parse_mode="Markdown")

    elif query.data == 'other_cmds':
        text = (
            "⚙️ *Access & Permission Control:*\n\n"
            "As an Admin, you can grant access to other users.\n\n"
            "👤 *Add User:*\n"
            "`/grant USER_ID`\n\n"
            "❌ *Remove User:*\n"
            "`/revoke USER_ID`\n\n"
            f"Your current Telegram ID: `{user_id}`"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]), parse_mode="Markdown")

    elif query.data == 'back_to_main':
        keyboard = [[InlineKeyboardButton("📊 Chat CMDs", callback_data='chat_cmds')], [InlineKeyboardButton("⚙️ Other CMDs (Access)", callback_data='other_cmds')]]
        await query.edit_message_text("👋 *Welcome to the Control Center.*\n\nSelect a category from the buttons below:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ---------------------------------------------------------------------------
# SIGNAL INTERPRETATION (angepasst)
# ---------------------------------------------------------------------------
async def handle_signal(update: Update, context: ContextTypes.DEFAULT_TYPE, is_long: bool):
    user_id = update.effective_user.id
    if not has_access(user_id):
        await update.message.reply_text("⛔ Unauthorized.")
        return

    args = context.args
    cmd_name = "long" if is_long else "short"
    if len(args) < 3:
        await update.message.reply_text(f"❌ Invalid Format.\nUsage:\n`/{cmd_name} Token entry 0.1000 -tp 0.1200 -sl 0.0700 -s 15 5`", parse_mode="Markdown")
        return
    try:
        coin = args[0].upper().split('/')[0]
        entry = args[2]
        tp1, lev, mar, sl = "N/A", "N/A", "N/A", "N/A"
        
        if "-tp" in args: tp1 = args[args.index("-tp") + 1]
        if "-sl" in args: sl = args[args.index("-sl") + 1]
        if "-s" in args:
            idx = args.index("-s")
            # Prüfen, ob nach -s noch mindestens ein Wert für Leverage kommt
            if len(args) > idx + 1:
                lev = args[idx + 1]
                # Prüfen, ob nach Leverage noch ein Wert für Margin kommt
                if len(args) > idx + 2 and not args[idx + 2].startswith("-"):
                    mar = args[idx + 2]
                else:
                    mar = "N/A"
            
        entry_str = f"`{entry}`" if entry != "N/A" else "N/A"
        if entry != "N/A": entry_str = f"${entry_str}"
        tp1_str = f"`{tp1}`" if tp1 != "N/A" else "N/A"
        if tp1 != "N/A": tp1_str = f"${tp1_str}"
        sl_str = f"`{sl}`" if sl != "N/A" else "N/A"
        if sl != "N/A": sl_str = f"${sl_str}"
            
        header_line = f"*📈 LONG - ${coin}*" if is_long else f"*📉 SHORT - ${coin}*"
            
        caption = (
            f"{header_line}\n\n"
            f"🏷 *Entry Price:* {entry_str}\n\n"
            f"✅ *TP1:* {tp1_str}\n\n"
            f"❌ *SL:* {sl_str}\n\n"
            f"_(Suggested Lev. {lev}x)_\n"
            f"_(Suggested Margin {mar}%)_"
        )
        
        status = await update.message.reply_text(f"🔄 Generating chart for {coin}...")
        path = fetch_live_chart_built_in(coin)
        with open(path, 'rb') as p:
            await update.message.reply_photo(photo=p, caption=caption, parse_mode="Markdown")
        os.remove(path)
        await status.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ Error.\nDetails: {e}")


async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_signal(update, context, is_long=False)

async def long_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_signal(update, context, is_long=True)

# ---------------------------------------------------------------------------
# ADMIN OPERATIONS
# ---------------------------------------------------------------------------
async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Only the main Admin can grant access.")
        return
    if not context.args:
        await update.message.reply_text("❌ Please specify a User ID. Example: `/grant 987654321`")
        return
    try:
        new_user = int(context.args[0])
        ALLOWED_USERS.add(new_user)
        await update.message.reply_text(f"✅ User ID `{new_user}` has been whitelisted!", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Invalid ID format.")

async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Only the main Admin can revoke access.")
        return
    if not context.args:
        await update.message.reply_text("❌ Please specify a User ID. Example: `/revoke 987654321`")
        return
    try:
        target_user = int(context.args[0])
        if target_user == ADMIN_ID:
            await update.message.reply_text("❌ You cannot revoke your own admin rights!")
            return
        if target_user in ALLOWED_USERS:
            ALLOWED_USERS.remove(target_user)
            await update.message.reply_text(f"❌ User ID `{target_user}` has been removed from the whitelist.", parse_mode="Markdown")
        else:
            await update.message.reply_text("ℹ️ This User ID was not active.")
    except ValueError:
        await update.message.reply_text("❌ Invalid ID format.")

# ---------------------------------------------------------------------------
# ENGINE START
# ---------------------------------------------------------------------------
def main():
    app = Application.builder().token("8975995836:AAEhxOhCGXPG4mDWtLtN_7eFx7RrcTMcNJ8").build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("short", short_command))
    app.add_handler(CommandHandler("long", long_command))
    app.add_handler(CommandHandler("grant", grant_command))
    app.add_handler(CommandHandler("revoke", revoke_command))
    app.add_handler(CallbackQueryHandler(button_tap_handler))
    print("Live Chart Engine Active... (Press Stop to terminate)")
    app.run_polling(close_loop=False)

if __name__ == '__main__':
    main()