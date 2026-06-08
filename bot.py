import os
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8893451999:AAEs0UG-Xya4_eU3Tg0myQ50I-dCSbWxzp8"
CHAT_ID = 6170764522

pending_reply = {}
pending_refund = {}
pending_review_reply = {}

def order_kb(order_id, user):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💬 Reply", callback_data=f"reply|{user}"),
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{order_id}"),
    ],[
        InlineKeyboardButton("↩️ Refund", callback_data=f"refund|{order_id}"),
    ]])

def review_kb(review_id, user):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💬 Reply to review", callback_data=f"review_reply|{review_id}|{user}")
    ]])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("FunPay Bot running. /help for commands.")

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text(
        "/help - commands\n"
        "/examples - notification examples\n"
        "/boost - boost offers\n"
        "/theme dark|light|red|blue\n"
        "/font serif|mono|modern\n"
        "/color red|white|yellow|green\n"
        "/bg dark|black|navy"
    )

async def examples_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("🛍 New purchase!\n👤 Username\n📦 Lot name\n💰 500₽", reply_markup=order_kb("123", "Username"))
    await update.message.reply_text("💬 Message from Username:\nHello, is it available?")
    await update.message.reply_text("⭐️ Review from Username\n⭐️⭐️⭐️⭐️⭐️\n💬 Great seller!", reply_markup=review_kb("456", "Username"))

async def boost_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    await update.message.reply_text("Open FunPay in Safari - script will boost offers.")

async def theme_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /theme dark|light|red|blue")
        return
    await update.message.reply_text(f"Theme '{args[0]}' set. Reload FunPay.")

async def font_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /font serif|mono|modern")
        return
    await update.message.reply_text(f"Font '{args[0]}' set. Reload FunPay.")

async def color_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /color red|white|yellow|green")
        return
    await update.message.reply_text(f"Color '{args[0]}' set. Reload FunPay.")

async def bg_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /bg dark|black|navy")
        return
    await update.message.reply_text(f"Background '{args[0]}' set. Reload FunPay.")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.message.chat.id != CHAT_ID: return
    d = q.data
    if d.startswith("reply|"):
        user = d.split("|")[1]
        pending_reply[CHAT_ID] = user
        await q.message.reply_text(f"Write message for {user}:")
    elif d.startswith("confirm|"):
        oid = d.split("|")[1]
        await q.message.reply_text(f"Order #{oid} confirmed.")
        await q.edit_message_reply_markup(reply_markup=None)
    elif d.startswith("refund|"):
        oid = d.split("|")[1]
        pending_refund[CHAT_ID] = oid
        await q.message.reply_text(f"Reason for refund #{oid}:")
    elif d.startswith("review_reply|"):
        parts = d.split("|")
        pending_review_reply[CHAT_ID] = (parts[1], parts[2] if len(parts) > 2 else "user")
        await q.message.reply_text("Write reply to review:")

async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID: return
    text = update.message.text
    cid = update.effective_chat.id
    if cid in pending_reply:
        user = pending_reply.pop(cid)
        ctx.bot_data[f"reply_{user}"] = text
        await update.message.reply_text(f"Message for {user} saved:\n{text}\nOpen FunPay chat.")
    elif cid in pending_refund:
        oid = pending_refund.pop(cid)
        await update.message.reply_text(f"Refund #{oid}, reason: {text}")
    elif cid in pending_review_reply:
        rid, user = pending_review_reply.pop(cid)
        await update.message.reply_text(f"Review reply for {user} saved:\n{text}")

async def handle_event(app, etype, data):
    if etype == "purchase":
        user = data.get("user", "")
        lot = data.get("lot", "")
        amount = data.get("amount", "")
        order_id = data.get("order_id", "0")
        if not user or not lot: return
        await app.bot.send_message(CHAT_ID, f"🛍 <b>New purchase!</b>\n\n👤 <b>{user}</b>\n📦 {lot}\n💰 {amount}₽", parse_mode="HTML", reply_markup=order_kb(order_id, user))
    elif etype == "message":
        user = data.get("user", "")
        msg = data.get("text", "")
        if not user or not msg: return
        await app.bot.send_message(CHAT_ID, f"💬 <b>Message from {user}:</b>\n{msg}", parse_mode="HTML")
    elif etype == "review":
        user = data.get("user", "")
        stars_count = int(data.get("stars", 0))
        txt = data.get("text", "").strip()
        review_id = data.get("review_id", "0")
        if not user or stars_count == 0: return
        stars = "⭐️" * stars_count
        await app.bot.send_message(CHAT_ID, f"⭐️ <b>Review from {user}</b>\n{stars}\n💬 {txt or 'empty'}", parse_mode="HTML", reply_markup=review_kb(review_id, user))

async def webhook(request):
    try:
        data = await request.json()
        await handle_event(request.app["tg"], data.get("type"), data)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)

async def health(request):
    return web.Response(text="OK")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("examples", examples_cmd))
    app.add_handler(CommandHandler("boost", boost_cmd))
    app.add_handler(CommandHandler("theme", theme_cmd))
    app.add_handler(CommandHandler("font", font_cmd))
    app.add_handler(CommandHandler("color", color_cmd))
    app.add_handler(CommandHandler("bg", bg_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        http = web.Application()
        http["tg"] = app
        http.router.add_post("/event", webhook)
        http.router.add_get("/", health)
        port = int(os.environ.get("PORT", 8080))
        runner = web.AppRunner(http)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", port).start()
        print(f"Started on port {port}")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
