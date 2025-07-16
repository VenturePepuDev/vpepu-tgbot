import httpx
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
VCPEPU = "0x2e709a0771203c3e7ac6bcc86c38557345e8164c"
VCPX = "0x9f8cd6824f758c7b2f34cc8a58493e0a66089e51"
GECKO_SIMPLE = "https://api.geckoterminal.com/api/v2/simple/networks/pepe-unchained/token_price/0x2e709a0771203c3e7ac6bcc86c38557345e8164c%2C0x9f8cd6824f758c7b2f34cc8a58493e0a66089e51?include_market_cap=true&mcap_fdv_fallback=true&include_24hr_vol=true&include_24hr_price_change=true"
PEPUSCAN_TOKENS_API = "https://pepuscan.com/api?module=account&action=tokenlist&address="
GECKO_LINKS = {
    "VCPEPU": "https://www.geckoterminal.com/pepe-unchained/pools/0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba",
    "VCPX": "https://www.geckoterminal.com/pepe-unchained/pools/0xba7fe75b9f2587397bb279a646e5b0a19adb6a1a"
}

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = httpx.get(GECKO_SIMPLE).json()
        a = r.get("data", {}).get("attributes", {})
        prices = a.get("token_prices", {})
        marketcaps = a.get("market_cap_usd", {})
        volumes = a.get("h24_volume_usd", {})
        changes = a.get("h24_price_change_percentage", {})

        tokens = {
            "VCPEPU": VCPEPU.lower(),
            "VCPX": VCPX.lower()
        }

        for name, addr in tokens.items():
            price = float(prices.get(addr, 0))
            mcap = float(marketcaps.get(addr, 0))
            vol = float(volumes.get(addr, 0))
            change = float(changes.get(addr, 0))

            msg = (
                f"📊 *{name} Price*\n"
                f"USD:        `${price:.9f}`\n"
                f"Marketcap:  `${mcap:,.2f}`\n"
                f"Vol (24h):  `${vol:,.2f}`\n"
                f"Change:     `{change:.2f}%`\n\n"
                f"[Geckoterminal]({GECKO_LINKS[name]}) | "
                f"[Pepuswap](https://www.pepuswap.com/) | "
                f"[Explorer](https://www.pepuscan.com/)"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching price: {e}")

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /wallet <0x...>")
    address = context.args[0].lower()
    url = f"{PEPUSCAN_TOKENS_API}{address}"
    try:
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(url)
            r.raise_for_status()
            tokens = r.json().get("result", [])

        for token in tokens:
            contract = token.get("contractAddress", "").lower()
            if contract in [VCPEPU.lower(), VCPX.lower()]:
                symbol = token.get("symbol", "?")
                balance = int(token.get("balance", "0")) / (10 ** int(token.get("decimals", "18")))
                short = address[:6] + "..." + address[-4:]
                msg = (
                    f"💰 *Wallet Check*\n"
                    f"Token:   `{symbol}`\n"
                    f"Address: `{short}`\n"
                    f"Balance: `{balance:,.2f}`"
                )
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching wallet: {e}")

async def ca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = (
            f"🔗 *VCPEPU Contract*\n"
            f"`{VCPEPU}`\n"
            f"[Explorer](https://pepuscan.com/address/{VCPEPU})\n\n"
            f"🔗 *VCPX Contract*\n"
            f"`{VCPX}`\n"
            f"[Explorer](https://pepuscan.com/address/{VCPX})"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def chapter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = httpx.get("https://api.geckoterminal.com/api/v2/networks/pepe-unchained/pools/0xfac9ffcf6a71c07f1b1fcf678270c8a3bdc30dba").json()
        fdv = float(r["data"]["attributes"]["fdv_usd"])
        unlocked = min(int(fdv // 10000) + 1, 15)
        row = ""
        for i in range(1, 16):
            row += f"{'✅' if i <= unlocked else '❌'} C{i}  "
        await update.message.reply_text(f"📘 *Unlocked Chapters*\n{row}", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .build()
)

app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("wallet", wallet))
app.add_handler(CommandHandler("ca", ca))
app.add_handler(CommandHandler("chapter", chapter))

if __name__ == "__main__":
    print("Bot is polling...")
    app.run_polling()
