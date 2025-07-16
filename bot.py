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
EXPLORER_API = "https://explorer-pepu-v2-mainnet-0.t.conduit.xyz/api/v2"
TOKEN_NAME = "VCPEPU"
TOKEN_ADDRESS = "0x2e709a0771203c3e7ac6bcc86c38557345e8164c"
TOKEN_VCPX_ADDRESS = "0x9f8cd6824f758c7b2f34cc8a58493e0a66089e51"
update_chat_id = 527577871
LAST_VCPEPU_TX = None
LAST_VCPX_TX = None

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
                tx_hash = latest["attributes"]["transaction_hash"]
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

# Init bot
app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .post_init(on_startup)
    .build()
)

app.add_handler(CommandHandler("price", lambda u, c: None))  # Platzhalter für spätere Befehle

if __name__ == "__main__":
    print("Bot is polling...")
    app.run_polling()
