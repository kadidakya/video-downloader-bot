
import os
import asyncio
import tempfile
import logging
from pathlib import Path

import yt_dlp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
MAX_SIZE = 49 * 1024 * 1024

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت تحميل الفيديوهات\n\n"
        "📥 أرسل رابط الفيديو وسأحاول تحميله.\n\n"
        "🌍 يدعم المواقع المتوافقة مع yt-dlp.\n"
        "🎬 أفضل جودة متاحة.\n"
        "⚡ تحميل تلقائي."
    )


def download_video(url, folder):
    options = {
        "outtmpl": str(Path(folder) / "%(id)s.%(ext)s"),
        "format": "best[ext=mp4][filesize<49M]/best[filesize<49M]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 2,
        "max_filesize": MAX_SIZE,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        downloads = info.get("requested_downloads") or []
        filename = (
            downloads[0].get("filepath")
            if downloads else ydl.prepare_filename(info)
        )

    path = Path(filename)

    if not path.exists():
        candidates = [
            p for p in Path(folder).glob("*") if p.is_file()
        ]
        if candidates:
            path = candidates[0]

    if not path.exists():
        raise Exception("لم يتم العثور على الفيديو")

    if path.stat().st_size > MAX_SIZE:
        raise Exception("حجم الفيديو أكبر من 49 ميغابايت")

    return path


async def receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith(("https://", "http://")):
        await update.message.reply_text("❌ أرسل رابطاً صحيحاً")
        return

    status = await update.message.reply_text(
        "⏳ جارٍ تحميل الفيديو..."
    )

    try:
        with tempfile.TemporaryDirectory() as folder:

            path = await asyncio.to_thread(
                download_video, url, folder
            )

            await status.edit_text("📤 جارٍ إرسال الفيديو...")

            with path.open("rb") as video:
                await update.message.reply_document(
                    document=video,
                    filename=path.name,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=30
                )

        await status.delete()

    except Exception as error:
        logger.exception("Download error")
        await status.edit_text(
            "❌ تعذر تحميل الفيديو.\n"
            "تأكد من صحة الرابط وأن الموقع يدعم التنزيل.\n"
            + str(error)[:200]
        )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN غير موجود في إعدادات الاستضافة")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive
        )
    )

    print("BOT STARTED SUCCESSFULLY")

    app.run_polling()


if __name__ == "__main__":
    main()
