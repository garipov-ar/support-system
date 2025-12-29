from django.core.management.base import BaseCommand
from django.conf import settings
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from apps.bot.bot import (
    start,
    category_handler,
    document_handler,
    back_handler,
)


class Command(BaseCommand):
    help = "Run Telegram bot"

    def handle(self, *args, **options):
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(category_handler, pattern="^cat:"))
        app.add_handler(CallbackQueryHandler(document_handler, pattern="^doc:"))
        app.add_handler(CallbackQueryHandler(back_handler, pattern="^back$"))

        print("🤖 Telegram bot started")
        app.run_polling()
