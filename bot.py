import os
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN   = os.environ.get("BOT_TOKEN", "8893451999:AAEs0UG-Xya4_eU3Tg0myQ50I-dCSbWxzp8")
CHAT_ID = int(os.environ.get("CHAT_ID", "6170764522"))

pending_reply = {}
pending_refund = {}
pending_review_reply = {}

def order_kb(order_id, user):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💬 Ответить", callback_data=f"reply|{user}"),
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm|{order_id}"),
    ],[
        InlineKeyboardButton("↩️ Возврат", callback_data=f"refund|{order_id}"),
    ]])

def review_kb(review_id, user):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💬 Ответить на отзыв", callback_data=f"review_reply|{review_id}|{user}")
    ]])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("👋 FunPay Bot запущен!\n\n/status — статус\n/balance — баланс\n/withdraw [сумма] — вывод\n/help — помощь")

async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("✅ Бот работает 24/7\n🟢 Онлайн")

async def balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("💰 Баланс: откройте FunPay → Финансы")

async def withdraw(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    args = ctx.args
    if not args:
        await update.message.reply_text("Укажите сумму: /withdraw 500")
        return
    await update.message.reply_text(f"↩️ Вывод {args[0]}₽ — FunPay → Финансы → Вывод средств")

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("📖 Кнопки:\n• 💬 Ответить покупателю\n• ✅ Подтвердить заказ\n• ↩️ Возврат\n• 💬 Ответить на отзыв\n\n/balance /withdraw /status")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.message.chat.id != CHAT_ID: return
    d = q.data
    if d.startswith("reply|"):
        user = d.split("|")[1]
        pending_reply[CHAT_ID] = user
        await q.message.reply_text(f"✏️ Напишите сообщение для {user}:")
    elif d.startswith("confirm|"):
        oid = d.split("|")[1]
        await q.message.reply_text(f"✅ Заказ #{oid} подтверждён")
        await q.edit_message_reply_markup(reply_markup=None)
    elif d.startswith("refund|"):
        oid = d.split("|")[1]
        pending_refund[CHAT_ID] = oid
        await q.message.reply_text(f"↩️ Причина возврата для #{oid}:")
    elif d.startswith("review_reply|"):
        parts = d.split("|")
        pending_review_reply[CHAT_ID] = (parts[1], parts[2] if len(parts) > 2 else "пользователь")
        await q.message.reply_text("✏️ Напишите ответ на отзыв:")

async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    text = update.message.text
    cid = update.effective_chat.id
    if cid in pending_reply:
        user = pending_reply.pop(cid)
        ctx.bot_data[f"reply_{user}"] = text
        await update.message.reply_text(f"📤 Сообщение для {user}:\n«{text}»\n\nОткройте чат на FunPay — скрипт вставит его.")
    elif cid in pending_refund:
        oid = pending_refund.pop(cid)
        await update.message.reply_text(f"↩️ Возврат #{oid}\nПричина: {text}\nОткройте FunPay → заказ #{oid}")
    elif cid in pending_review_reply:
        rid, user = pending_review_reply.pop(cid)
        await update.message.reply_text(f"💬 Ответ на отзыв {user}:\n«{text}»\nОткройте FunPay → отзывы")

async def handle_event(app, etype, data):
    if etype == "purchase":
        text = f"🛍 <b>Новая покупка!</b>\n\n👤 <b>{data.get('user')}</b> оплатил покупку\n📦 {data.get('lot')}\n💰 {data.get('amount')}₽"
        await app.bot.send_message(CHAT_ID, text, parse_mode="HTML", reply_markup=order_kb(data.get("order_id","0"), data.get("user","")))
    elif etype == "message":
        await app.bot.send_message(CHAT_ID, f"💬 <b>Сообщение от {data.get('user')}:</b>\n{data.get('text')}", parse_mode="HTML")
    elif etype == "review":
        stars = "⭐️" * int(data.get("stars", 5))
        txt = data.get("text","").strip() or "пусто…"
        await app.bot.send_message(CHAT_ID, f"⭐️ <b>Отзыв от {data.get('user')}</b>\n{stars}\n💬 {txt}", parse_mode="HTML", reply_markup=review_kb(data.get("review_id","0"), data.get("user","")))

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
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    async with tg_app:
        await tg_app.start()
        await tg_app.updater.start_polling(drop_pending_updates=True)
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
