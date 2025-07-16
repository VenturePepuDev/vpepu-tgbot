import httpx
import asyncio
import certifi
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
POOL_API = "https://api.geckoterminal.com/api/v2/networks/pepe-unchained/pools/0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba"
EXPLORER_API = "https://explorer-pepu-v2-mainnet-0.t.conduit.xyz/api/v2"
TOKEN_NAME = "VCPEPU"
TOKEN_ADDRESS = "0x2e709a0771203c3e7ac6bcc86c38557345e8164c"
update_chat_id = 527577871
LAST_TX_HASH = None

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = httpx.get(POOL_API, verify=certifi.where()).json()
    usd = r["data"]["attributes"]["base_token_price_usd"]
    wpepu = r["data"]["attributes"]["quote_token_price_native_currency"]
    await update.message.reply_text(f"\ud83d\udcb1 {TOKEN_NAME} Price\nUSD \xa6 {usd[:11]}\nWPEPU \xa6 {wpepu[:8]}")

async def ca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"\ud83d\udd17 Contract\n{TOKEN_NAME} \xa6 {TOKEN_ADDRESS}")

async def mcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = httpx.get(POOL_API, verify=certifi.where()).json()
    fdv = float(r["data"]["attributes"]["fdv_usd"])
    await update.message.reply_text(f"\ud83d\udcca FDV (Market Cap)\nUSD \xa6 ${fdv:,.2f}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = httpx.get(POOL_API, verify=certifi.where()).json()
    a = r["data"]["attributes"]
    usd = a["base_token_price_usd"][:11]
    wpepu = a["quote_token_price_native_currency"][:8]
    holders = a.get("base_token", {}).get("number_of_holders", "?")
    v24 = float(a["volume_usd"]["h24"])
    v1 = float(a["volume_usd"]["h1"])
    fdv = float(a["fdv_usd"])
    msg = f"\u2139\ufe0f {TOKEN_NAME} Info\nUSD \xa6 {usd}\nWPEPU \xa6 {wpepu}\nHolders \xa6 {holders}\n24h Volume \xa6 ${v24:,.2f}\n1h Volume \xa6 ${v1:,.2f}\nFDV \xa6 ${fdv:,.2f}"
    await update.message.reply_text(msg)

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("\u26a0\ufe0f Usage: /wallet <0x...>")
    address = context.args[0].lower()
    url = f"{EXPLORER_API}/addresses/{address}/token-balances"
    try:
        r = httpx.get(url, verify=certifi.where())
        r.raise_for_status()
        data = r.json()
        balances = data.get("items", [])
        match = next((x for x in balances if x.get("token", {}).get("contract_address", "").lower() == TOKEN_ADDRESS.lower()), None)
        if match:
            raw = int(match.get("balance", "0"))
            amount = raw / 1e18
            short = address[:6] + "..." + address[-4:]
            await update.message.reply_text(
                f"\ud83d\udcbb Wallet Check\nAddress \xa6 {short}\n{TOKEN_NAME} \xa6 {amount:,.4f}"
            )
        else:
            await update.message.reply_text(f"{TOKEN_NAME} not found in wallet.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching wallet data: {e}")

async def chapter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = httpx.get(POOL_API, verify=certifi.where()).json()
    fdv = float(r["data"]["attributes"]["fdv_usd"])
    unlocked = int(fdv // 10000) + 1
    unlocked = min(unlocked, 15)
    out = "\ud83d\udcd8 Unlocked Chapters\n\n"
    for i in range(1, 16):
        if i <= unlocked:
            out += f"\u2705 C{i} \xa6 "
        else:
            out += f"\u274c C{i} \xa6 "
    await update.message.reply_text(out.rstrip(" \xa6 "))

# Init bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("ca", ca))
app.add_handler(CommandHandler("mcap", mcap))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("wallet", wallet))
app.add_handler(CommandHandler("chapter", chapter))

if __name__ == "__main__":
    app.run_polling()
