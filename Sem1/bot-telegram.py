import ccxt
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TOKEN_TG")

# Diccionario en memoria para guardar alertas activas
# Estructura: { chat_id: [ {simbolo, precio_objetivo, direccion}, ... ] }
alertas_activas = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def obtener_precio(simbolo: str) -> float:
    """Obtiene el precio actual de un par en Binance."""
    try:
        binance = ccxt.binance()
        ticker = binance.fetch_ticker(f'{simbolo}/USDT')
        return float(ticker['last'])
    except Exception as e:
        logging.error(f"Error al obtener precio de {simbolo}: {e}")
        return None


async def revisar_alertas(bot):
    """
    Tarea que corre cada 5 minutos.
    Revisa todas las alertas activas y notifica si se cumple la condición.
    """
    if not alertas_activas:
        return

    logging.info("Revisando alertas activas...")

    for chat_id, lista_alertas in list(alertas_activas.items()):
        alertas_a_eliminar = []

        for alerta in lista_alertas:
            simbolo = alerta['simbolo']
            precio_objetivo = alerta['precio_objetivo']
            direccion = alerta['direccion']  # 'sube' o 'baja'

            precio_actual = obtener_precio(simbolo)

            if precio_actual is None:
                continue

            condicion_cumplida = (
                direccion == 'sube' and precio_actual >= precio_objetivo or
                direccion == 'baja' and precio_actual <= precio_objetivo
            )

            if condicion_cumplida:
                mensaje = (
                    f"🚨 *Alerta activada*\n"
                    f"*{simbolo}/USDT* llegó a *${precio_actual:,.2f}*\n"
                    f"Tu objetivo era: ${precio_objetivo:,.2f}"
                )
                await bot.send_message(
                    chat_id=chat_id,
                    text=mensaje,
                    parse_mode='Markdown'
                )
                alertas_a_eliminar.append(alerta)
                logging.info(f"Alerta disparada: {simbolo} @ {precio_actual} para chat {chat_id}")

        # Eliminar alertas que ya se dispararon
        for alerta in alertas_a_eliminar:
            lista_alertas.remove(alerta)


# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "👋 Hola, soy tu bot de alertas crypto.\n\n"
        "*Comandos disponibles:*\n"
        "/btc — Precio actual de Bitcoin\n"
        "/alerta [SIMBOLO] [PRECIO] — Crear alerta de precio\n"
        "  Ejemplo: `/alerta BTC 95000`\n"
        "/mis\\_alertas — Ver tus alertas activas\n"
        "/cancelar\\_alertas — Eliminar todas tus alertas"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')


async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    precio = obtener_precio('BTC')
    if precio:
        await update.message.reply_text(f"₿ *BTC/USDT:* ${precio:,.2f}", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Error al obtener el precio. Intenta de nuevo.")


async def alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Uso: /alerta BTC 95000
    Detecta automáticamente si la alerta es hacia arriba o hacia abajo
    comparando con el precio actual.
    """
    # Validar argumentos
    if len(context.args) != 2:
        await update.message.reply_text(
            "⚠️ Uso correcto: `/alerta SIMBOLO PRECIO`\nEjemplo: `/alerta BTC 95000`",
            parse_mode='Markdown'
        )
        return

    simbolo = context.args[0].upper()
    
    try:
        precio_objetivo = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ El precio debe ser un número. Ejemplo: `/alerta BTC 95000`", parse_mode='Markdown')
        return

    # Obtener precio actual para determinar dirección
    precio_actual = obtener_precio(simbolo)
    
    if precio_actual is None:
        await update.message.reply_text(f"❌ No encontré el par {simbolo}/USDT en Binance. Verifica el símbolo.")
        return

    direccion = 'sube' if precio_objetivo > precio_actual else 'baja'
    chat_id = update.effective_chat.id

    # Guardar alerta
    if chat_id not in alertas_activas:
        alertas_activas[chat_id] = []

    alertas_activas[chat_id].append({
        'simbolo': simbolo,
        'precio_objetivo': precio_objetivo,
        'direccion': direccion
    })

    emoji = "📈" if direccion == 'sube' else "📉"
    await update.message.reply_text(
        f"✅ *Alerta creada*\n"
        f"{emoji} Te aviso cuando *{simbolo}/USDT* llegue a *${precio_objetivo:,.2f}*\n"
        f"Precio actual: ${precio_actual:,.2f}",
        parse_mode='Markdown'
    )


async def mis_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    alertas = alertas_activas.get(chat_id, [])

    if not alertas:
        await update.message.reply_text("No tienes alertas activas.")
        return

    mensaje = "🔔 *Tus alertas activas:*\n\n"
    for i, a in enumerate(alertas, 1):
        emoji = "📈" if a['direccion'] == 'sube' else "📉"
        mensaje += f"{i}. {emoji} {a['simbolo']}/USDT → ${a['precio_objetivo']:,.2f}\n"

    await update.message.reply_text(mensaje, parse_mode='Markdown')


async def cancelar_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in alertas_activas:
        cantidad = len(alertas_activas[chat_id])
        del alertas_activas[chat_id]
        await update.message.reply_text(f"🗑️ {cantidad} alerta(s) eliminada(s).")
    else:
        await update.message.reply_text("No tenías alertas activas.")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Registrar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("alerta", alerta))
    app.add_handler(CommandHandler("mis_alertas", mis_alertas))
    app.add_handler(CommandHandler("cancelar_alertas", cancelar_alertas))

    # Configurar scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        revisar_alertas,
        trigger='interval',
        minutes=5,
        args=[app.bot]
    )
    scheduler.start()

    logging.info("Bot iniciado con scheduler de alertas activo.")
    app.run_polling()
