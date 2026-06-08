import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from aiohttp import web

TOKEN   = os.environ.get("BOT_TOKEN", "8893451999:AAEs0UG-Xya4_eU3Tg0myQ50I-dCSbWxzp8")
CHAT_ID = int(os.environ.get("CHAT_ID", "6170764522"))

pending_reply = {}
pending_refund = {}
pending_review_reply = {}

def order_keyboard(order_id, funpay_user):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ответить", callback_data=f"reply|{funpay_user}"),
         InlineKeyboardButton("✅ Подтвердить заказ", callback_data=f"confirm|{order_id}")],
        [InlineKeyboardButton("↩️ Сделать возврат", callback_data=f"refund|{order_id}")]
    ])

def review_keyboard(review_id, funpay_user):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ответить на отзыв", callback_data=f"review_reply|{review_id}|{funpay_user}")]
    ])

async def start(update, ctx):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("👋 FunPay Helper Bot запущен!\n\n/balance — баланс\n/withdraw [сумма] — вывод\n/status — статус\n/help — помощь")

async def status(update, ctx):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("✅ Бот работает 24/7\n🟢 FunPay мониторинг активен")

async def balance(update, ctx):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("💰 Баланс доступен на FunPay → Финансы")

async def withdraw(update, ctx):
    if update.effective_chat.id != CHAT_ID: return
    args = ctx.args
    if not args:
        await update.message.reply_text("Укажите сумму: /withdraw 500")
        return
    await update.message.reply_text(f"↩️ Вывод {args[0]}₽ — откройте FunPay → Финансы → Вывод средств")

async def help_cmd(update, ctx):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("📖 Кнопки при покупке:\n• 💬 Ответить\n• ✅ Подтвердить заказ\n• ↩️ Возврат\n• 💬 Ответить на отзыв\n\nКоманды:\n/balance /withdraw /status")

async def button_handler(update, ctx):
    query = update.callback_query
    await query.answer()
    if query.message.chat.id != CHAT_ID: return
    data = query.data
    if data.startswith("reply|"):
        user = data.split("|")[1]
        pending_reply[CHAT_ID] = user
        await query.message.reply_text(f"✏️ Напишите сообщение для {user}:")
    elif data.startswith("confirm|"):
        oid = data.split("|")[1]
        await query.message.reply_text(f"✅ Заказ #{oid} подтверждён")
        await query.edit_message_reply_markup(reply_markup=None)
    elif data.startswith("refund|"):
        oid = data.split("|")[1]
        pending_refund[CHAT_ID] = oid
        await query.message.reply_text(f"↩️ Причина возврата для #{oid}:")
    elif data.startswith("review_reply|"):
        parts = data.split("|")
        pending_review_reply[CHAT_ID] = (parts[1], parts[2] if len(parts) > 2 else "пользователь")
        await query.message.reply_text(f"✏️ Напишите ответ на отзыв:")

async def message_handler(update, ctx):
    if update.effective_chat.id != CHAT_ID: return
    text = update.message.text
    cid = update.effective_chat.id
    if cid in pending_reply:
        user = pending_reply.pop(cid)
        ctx.bot_data[f"reply_{user}"] = text
        await update.message.reply_text(f"📤 Сообщение для {user}:\n«{text}»\n\nОткройте чат на FunPay — скрипт вставит его автоматически.")
    elif cid in pending_refund:
        oid = pending_refund.pop(cid)
        await update.message.reply_text(f"↩️ Возврат #{oid}\nПричина: {text}\n\nОткройте FunPay → заказ #{oid}")
    elif cid in pending_review_reply:
        rid, user = pending_review_reply.pop(cid)
        await update.message.reply_text(f"💬 Ответ на отзыв {user}:\n«{text}»\n\nОткройте FunPay → отзывы")

async def handle_event(app, etype, data):
    if etype == "purchase":
        stars = "⭐️" * int(data.get("stars", 0))
        text = f"🛍 <b>Новая покупка!</b>\n\n👤 <b>{data.get('user')}</b> оплатил покупку\n📦 {data.get('lot')}\n💰 {data.get('amount')}₽"
        await app.bot.send_message(CHAT_ID, text, parse_mode="HTML", reply_markup=order_keyboard(data.get("order_id","0"), data.get("user")))
    elif etype == "message":
        await app.bot.send_message(CHAT_ID, f"💬 <b>Сообщение от {data.get('user')}:</b>\n{data.get('text')}", parse_mode="HTML")
    elif etype == "review":
        stars = "⭐️" * int(data.get("stars", 5))
        txt = data.get("text","").strip() or "пусто…"
        await app.bot.send_message(CHAT_ID, f"⭐️ <b>Отзыв от {data.get('user')}</b>\n{stars}\n💬 {txt}", parse_mode="HTML", reply_markup=review_keyboard(data.get("review_id","0"), data.get("user")))

async def webhook_handler(request):
    try:
        data = await request.json()
        await handle_event(request.app["tg_app"], data.get("type"), data)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)

async def health(request):
    return web.Response(text="OK")

async def main():
    tg_app = Application.builder().token(TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("status", status))
    tg_app.add_handler(CommandHandler("balance", balance))
    tg_app.add_handler(CommandHandler("withdraw", withdraw))
    tg_app.add_handler(CommandHandler("help", help_cmd))
    tg_app.add_handler(CallbackQueryHandler(button_handler))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    http_app = web.Application()
    http_app["tg_app"] = tg_app
    http_app.router.add_post("/funpay-event", webhook_handler)
    http_app.router.add_get("/", health)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(http_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"✅ Бот запущен на порту {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
