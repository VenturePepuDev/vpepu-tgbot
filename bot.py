import httpx
import asyncio
import certifi
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
POOL_API_VCPEPU = "https://api.geckoterminal.com/api/v2/networks/pepe-unchained/pools/0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba/trades"
POOL_API_VCPX = "https://api.geckoterminal.com/api/v2/networks/pepe-unchained/pools/0x9f8cd6824f758c7b2f34cc8a58493e0a66089e51/trades"
GECKO_API = "https://api.geckoterminal.com/api/v2/networks/pepe-unchained/pools/0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba"
EXPLORER_API = "https://explorer-pepu-v2-mainnet-0.t.conduit.xyz/api/v2"
TOKEN_VCPEPU = "0x2e709a0771203c3e7ac6bcc86c38557345e8164c"
TOKEN_VCPX = "0x9f8cd6824f758c7b2f34cc8a58493e0a66089e51"
update_chat_id = 527577871
LAST_VCPEPU_TX = None
LAST_VCPX_TX = None

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = httpx.get(GECKO_API, verify=certifi.where()).json()
    a = r["data"]["attributes"]
    usd = a["base_token_price_usd"][:11]
    wpepu = a["quote_token_price_native_currency"][:8]
    change = a.get("price_change_percentage", {}).get("h24")
    if change:
        change = float(change)
        change_fmt = f"{change:+.2f}%"
    else:
        change_fmt = "?"
    await update.message.reply_text(
        f"💱 VCPEPU Price\nUSD ¦ ${usd}\nWPEPU ¦ {wpepu}\n24h Change ¦ {change_fmt}"
    )

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /wallet <0x...>")
    address = context.args[0].lower()
    url = f"{EXPLORER_API}/addresses/{address}/token-balances"
    try:
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            balances = data.get("items", [])
            vcp = next((x for x in balances if x.get("token", {}).get("contract_address", "").lower() == TOKEN_VCPEPU.lower()), None)
            vpx = next((x for x in balances if x.get("token", {}).get("contract_address", "").lower() == TOKEN_VCPX.lower()), None)
            raw1 = int(vcp.get("balance", 0)) / 1e18 if vcp else 0
            raw2 = int(vpx.get("balance", 0)) / 1e18 if vpx else 0
            short = address[:6] + "..." + address[-4:]
            await update.message.reply_text(
                f"👛 Wallet Check\nAddress ¦ {short}\nVCPEPU ¦ {raw1:,.2f}\nVCPX ¦ {raw2:,.2f}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching wallet data: {e}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(verify=False) as client:
            vcpepu_info = await client.get(f"{EXPLORER_API}/tokens/{TOKEN_VCPEPU}")
            vcpx_info = await client.get(f"{EXPLORER_API}/tokens/{TOKEN_VCPX}")
            vcpepu_holders = await client.get(f"{EXPLORER_API}/tokens/{TOKEN_VCPEPU}/holders")
            vcpx_holders = await client.get(f"{EXPLORER_API}/tokens/{TOKEN_VCPX}/holders")

        vcpepu_price = float(vcpepu_info.json().get("price_usd", 0))
        vcpx_price = float(vcpx_info.json().get("price_usd", 0))
        vcpepu_count = vcpepu_holders.json().get("totalItems", "?")
        vcpx_count = vcpx_holders.json().get("totalItems", "?")

        await update.message.reply_text(
            f"ℹ️ Token Info\n"
            f"VCPEPU ¦ ${vcpepu_price:.8f} ¦ Holders: {vcpepu_count}\n"
            f"VCPX   ¦ ${vcpx_price:.8f} ¦ Holders: {vcpx_count}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching token info: {e}")

async def mcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = httpx.get(GECKO_API, verify=certifi.where()).json()
    fdv = float(r["data"]["attributes"]["fdv_usd"])
    await update.message.reply_text(f"📊 FDV (Market Cap)\nUSD ¦ ${fdv:,.2f}")

async def ca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🔗 Contract\nVCPEPU ¦ {TOKEN_VCPEPU}\nVCPX ¦ {TOKEN_VCPX}")

async def chapter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = httpx.get(GECKO_API, verify=certifi.where()).json()
    fdv = float(r["data"]["attributes"]["fdv_usd"])
    unlocked = int(fdv // 10000) + 1
    unlocked = min(unlocked, 15)
    out = "📘 Unlocked Chapters\n\n"
    for i in range(1, 16):
        if i <= unlocked:
            out += f"✅ C{i} ¦ "
        else:
            out += f"❌ C{i} ¦ "
    await update.message.reply_text(out.rstrip(" ¦ "))

async def monitor_buys(app):
    global LAST_VCPEPU_TX, LAST_VCPX_TX
    await asyncio.sleep(5)
    while True:
        try:
            for token, url, last_tx in [
                ("VCPEPU", POOL_API_VCPEPU, LAST_VCPEPU_TX),
                ("VCPX", POOL_API_VCPX, LAST_VCPX_TX),
            ]:
                r = httpx.get(url, verify=certifi.where())
                data = r.json().get("data", [])
                if not data:
                    continue
                latest = data[0]
                tx_hash = latest["id"]
                amount_usd = float(latest["attributes"].get("amount_in_usd", 0))
                if latest["attributes"].get("trade_type") != "buy" or amount_usd < 1:
                    continue
                if (token == "VCPEPU" and tx_hash == LAST_VCPEPU_TX) or (token == "VCPX" and tx_hash == LAST_VCPX_TX):
                    continue
                if token == "VCPEPU":
                    LAST_VCPEPU_TX = tx_hash
                    pool = "0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba"
                else:
                    LAST_VCPX_TX = tx_hash
                    pool = "0x9f8cd6824f758c7b2f34cc8a58493e0a66089e51"

                buyer = latest["attributes"].get("maker_address", "?")
                price = latest["attributes"].get("token_price_usd", "?")
                amount = latest["attributes"].get("token_amount", "?")

                tx_url = f"https://pepuscan.com/tx/{tx_hash}"
                wallet_url = f"https://pepuscan.com/address/{buyer}"
                trade_url = f"https://www.geckoterminal.com/pepe-unchained/pools/{pool}/txs/{tx_hash}"
                short_wallet = buyer[:6] + "..." + buyer[-4:]

                alert = (
                    f"🚨 New {token} Buy Detected!\n"
                    f"{token} ¦ ${amount_usd:.2f}\n"
                    f"Tx ¦ [Tx]({tx_url})\n"
                    f"From ¦ [From]({wallet_url})\n"
                    f"Trade ¦ [Trade]({trade_url})"
                )

                details = (
                    f"📦 Buy Alert\n"
                    f"Buyer: {short_wallet}\n"
                    f"{token} Amount: {amount}\n"
                    f"Price: ${price}\n"
                    f"Volume: ${amount_usd:.2f}\n"
                    f"Market Cap: [Link](https://www.geckoterminal.com/pepe-unchained/pools/{pool})"
                )

                await app.bot.send_message(chat_id=update_chat_id, text=alert, parse_mode=ParseMode.MARKDOWN)
                await app.bot.send_message(chat_id=update_chat_id, text=details, parse_mode=ParseMode.MARKDOWN)
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

app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("wallet", wallet))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("mcap", mcap))
app.add_handler(CommandHandler("ca", ca))
app.add_handler(CommandHandler("chapter", chapter))

if __name__ == "__main__":
    print("Bot is polling...")
    app.run_polling()
