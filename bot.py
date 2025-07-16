import httpx
import asyncio
import certifi
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
VCPEPU = "0x2e709a0771203c3e7ac6bcc86c38557345e8164c"
VCPX = "0x9f8cd6824f758c7b2f34cc8a58493e0a66089e51"
GECKO_SIMPLE = f"https://api.geckoterminal.com/api/v2/simple/networks/pepe-unchained/token_price/{VCPEPU},{VCPX}?include_market_cap=true&mcap_fdv_fallback=true&include_24hr_vol=true&include_24hr_price_change=true"
POOL_API_VCPEPU = "https://api.geckoterminal.com/api/v2/networks/pepe-unchained/pools/0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba/trades"
POOL_API_VCPX = "https://api.geckoterminal.com/api/v2/networks/pepe-unchained/pools/0xba7fe75b9f2587397bb279a646e5b0a19adb6a1a/trades"
HOLDERS_API_VCPEPU = f"https://explorer-pepu-v2-mainnet-0.t.conduit.xyz/api/v2/tokens/{VCPEPU}/holders"
HOLDERS_API_VCPX = f"https://explorer-pepu-v2-mainnet-0.t.conduit.xyz/api/v2/tokens/{VCPX}/holders"
GECKO_POOL = "https://api.geckoterminal.com/api/v2/networks/pepe-unchained/pools/0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba"
update_chat_id = 527577871
LAST_VCPEPU_TX = None
LAST_VCPX_TX = None

async def ca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🔗 Contract\nVCPEPU ¦ {VCPEPU}\nVCPX ¦ {VCPX}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(verify=False) as client:
            price_data = await client.get(GECKO_SIMPLE)
            holders_vcpepu = await client.get(HOLDERS_API_VCPEPU)
            holders_vcpx = await client.get(HOLDERS_API_VCPX)

        prices = price_data.json().get("data", {})
        vcpepu_data = prices.get(VCPEPU.lower(), {})
        vcpx_data = prices.get(VCPX.lower(), {})

        vcpepu_price = vcpepu_data.get("token_price_usd", "?")
        vcpx_price = vcpx_data.get("token_price_usd", "?")
        vcpepu_holders = holders_vcpepu.json().get("totalItems", "?")
        vcpx_holders = holders_vcpx.json().get("totalItems", "?")

        await update.message.reply_text(
            f"ℹ️ Token Info\n"
            f"VCPEPU ¦ ${vcpepu_price} ¦ Holders: {vcpepu_holders}\n"
            f"VCPX   ¦ ${vcpx_price} ¦ Holders: {vcpx_holders}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching info: {e}")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = httpx.get(GECKO_SIMPLE).json().get("data", {})
        vcpepu = r.get(VCPEPU.lower(), {})
        vcpx = r.get(VCPX.lower(), {})

        msg = ""
        for name, token in [("VCPEPU", vcpepu), ("VCPX", vcpx)]:
            msg += f"💱 {name} Price\n"
            msg += f"USD ¦ ${token.get('token_price_usd', '?')}\n"
            msg += f"FDV ¦ ${token.get('fdv_usd', '?')}\n"
            msg += f"Vol 24h ¦ ${token.get('volume_usd', {}).get('h24', '?')}\n"
            msg += f"24h Change ¦ {token.get('price_change_percentage', {}).get('h24', '?')}%\n\n"

        await update.message.reply_text(msg.strip())
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching price: {e}")

async def chapter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = httpx.get(GECKO_POOL).json()
        fdv = float(r["data"]["attributes"]["fdv_usd"])
        unlocked = min(int(fdv // 10000) + 1, 15)
        out = "📘 Unlocked Chapters\n\n"
        for i in range(1, 16):
            out += f"{'✅' if i <= unlocked else '❌'} C{i} ¦ "
        await update.message.reply_text(out.rstrip(" ¦ "))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /wallet <0x...>")
    address = context.args[0].lower()
    try:
        async with httpx.AsyncClient(verify=False) as client:
            holders_vcpepu = await client.get(HOLDERS_API_VCPEPU)
            holders_vcpx = await client.get(HOLDERS_API_VCPX)

        def find_balance(data):
            for h in data.get("items", []):
                if h.get("holder_address", "").lower() == address:
                    return int(h.get("balance", 0)) / 1e18
            return 0

        vcpepu_amt = find_balance(holders_vcpepu.json())
        vcpx_amt = find_balance(holders_vcpx.json())
        short = address[:6] + "..." + address[-4:]
        await update.message.reply_text(
            f"👛 Wallet Check\nAddress ¦ {short}\nVCPEPU ¦ {vcpepu_amt:,.2f}\nVCPX ¦ {vcpx_amt:,.2f}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching wallet: {e}")

async def monitor_buys(app):
    global LAST_VCPEPU_TX, LAST_VCPX_TX
    await asyncio.sleep(5)
    while True:
        try:
            for token, url, last_tx in [
                ("VCPEPU", POOL_API_VCPEPU, LAST_VCPEPU_TX),
                ("VCPX", POOL_API_VCPX, LAST_VCPX_TX),
            ]:
                r = httpx.get(url).json().get("data", [])
                if not r:
                    continue
                tx = r[0]
                tx_hash = tx["id"]
                if tx_hash == last_tx:
                    continue
                amount = float(tx["attributes"].get("amount_in_usd", 0))
                if amount < 5 or tx["attributes"].get("trade_type") != "buy":
                    continue
                if token == "VCPEPU":
                    LAST_VCPEPU_TX = tx_hash
                    pool = "0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba"
                else:
                    LAST_VCPX_TX = tx_hash
                    pool = "0xba7fe75b9f2587397bb279a646e5b0a19adb6a1a"

                addr = tx["attributes"].get("maker_address", "?")
                short = addr[:6] + "..." + addr[-4:]
                trade_link = f"https://www.geckoterminal.com/pepe-unchained/pools/{pool}/txs/{tx_hash}"
                tx_link = f"https://pepuscan.com/tx/{tx_hash}"
                from_link = f"https://pepuscan.com/address/{addr}"

                alert = (
                    f"🚨 New {token} Buy Detected!\n{token} ¦ ${amount:.2f}\n"
                    f"Tx ¦ [Tx]({tx_link})\nFrom ¦ [From]({from_link})\nTrade ¦ [Trade]({trade_link})"
                )
                await app.bot.send_message(chat_id=update_chat_id, text=alert, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            print("Buy monitor error:", e)
        await asyncio.sleep(15)

async def on_startup(app):
    asyncio.create_task(monitor_buys(app))

app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .post_init(on_startup)
    .build()
)

app.add_handler(CommandHandler("ca", ca))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("chapter", chapter))
app.add_handler(CommandHandler("wallet", wallet))

if __name__ == "__main__":
    print("Bot is polling...")
    app.run_polling()
