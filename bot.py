import os
import asyncio
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = "8672168855:AAH2jDHFZMOUQ-QbhRwlvfb3QpKE_aV-ut8"

user_links = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь ссылку на видео — выберешь качество и я скачаю."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    user_links[user_id] = url

    await update.message.reply_text("⏳ Получаю доступные качества...")

    try:
        result = subprocess.run(
            ["yt-dlp", "-F", url],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.splitlines()

        qualities = {}
        for line in lines:
            for res in ["144", "240", "360", "720", "1080", "1440", "2160"]:
                if res+"p" in line or f"x{res}" in line or f"{res}p" in line:
                    if res not in qualities:
                        for part in line.split():
                            if part.isdigit() or part.startswith("format"):
                                qualities[res] = line.split()[0]
                                break

        if not qualities:
            await update.message.reply_text("❌ Не удалось получить качества. Проверь ссылку.")
            return

        labels = {"144":"144p","240":"240p","360":"360p","720":"720p","1080":"1080p","1440":"2K","2160":"4K"}
        keyboard = [
            [InlineKeyboardButton(labels.get(res, res+"p"), callback_data=f"dl:{res}:{user_id}")]
            for res in sorted(qualities.keys(), key=lambda x: int(x))
        ]
        await update.message.reply_text("Выбери качество:", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, res, user_id = query.data.split(":")
    user_id = int(user_id)
    url = user_links.get(user_id)

    if not url:
        await query.edit_message_text("Ссылка не найдена. Отправь заново.")
        return

    await query.edit_message_text(f"⏳ Скачиваю {res}p...")

    output = f"video_{user_id}.mp4"

    try:
        subprocess.run([
            "yt-dlp",
            "-f", f"bestvideo[height<={res}]+bestaudio/best[height<={res}]",
            "--merge-output-format", "mp4",
            "-o", output,
            url
        ], check=True, timeout=300)

        await query.edit_message_text("✅ Отправляю...")

        with open(output, "rb") as f:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=f,
                supports_streaming=True
            )

    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}")

    finally:
        if os.path.exists(output):
            os.remove(output)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_quality, pattern=r"^dl:"))
    app.run_polling()

if __name__ == "__main__":
    main()
