from django.core.management.base import BaseCommand
from django.conf import settings
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from apps.bot.bot import search_handler


from apps.bot.bot import (
    start,
    category_handler,
    document_handler,
    back_handler,
    agreement_handler,
    receive_name,
    receive_email,
    cancel,
    ASK_NAME,
    ASK_EMAIL,
    ASK_CONSENT
)


class Command(BaseCommand):
    help = "Run Telegram bot"

    def handle(self, *args, **options):
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

        # Registration Conversation
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
                ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
                ASK_CONSENT: [CallbackQueryHandler(agreement_handler, pattern="^agree_policy$")],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )

        app.add_handler(conv_handler)

        app.add_handler(CallbackQueryHandler(category_handler, pattern="^cat:"))
        app.add_handler(CallbackQueryHandler(document_handler, pattern="^doc:"))
        app.add_handler(CallbackQueryHandler(back_handler, pattern="^back$"))
        app.add_handler(CommandHandler("search", search_handler))

        print("🤖 Telegram bot started")
        app.run_polling()
