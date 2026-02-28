import ccxt  # DOCUMENTACION OFICIAL DE LA LIBRERIA: https://docs.ccxt.com/README
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TOKEN_TG")
USER = os.getenv("USER")


def precio_btc():

    # Instanciar el exchange
    binance = ccxt.binance()

    # Obtener el precio actual de Bitcoin
    ticker = binance.fetch_ticker('BTC/USDT')
    print(f"Precio actual: {ticker['last']}")
    print(f"ticker: {ticker}")
    print(f"tipo: {type(ticker)}")

    return ticker


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de Telegram.")

async def btc(update: Update, contex: ContextTypes.DEFAULT_TYPE):

    try:

        precio = precio_btc()
        await update.message.reply_text(f"este es el precio del BTC actualmente: {precio['last']} $")

    except Exception as e:
        print(f"erorr al intentar obtener el precio del bitcoin: {e}")

if __name__ ==  "__main__":
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("btc", btc))

    app.run_polling()





# print(ccxt.exchanges) # print a list of all available exchange classes
