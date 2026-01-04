from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from apps.bot.bot import search_handler
from asgiref.sync import sync_to_async
import asyncio
import logging

logger = logging.getLogger(__name__)

from apps.bot.bot import (
    start,
    category_handler,
    document_handler,
    back_handler,
    agreement_handler,
    receive_name,
    receive_email,
    cancel,
    toggle_subscription_handler,
    initiate_search_handler,
    handle_search_query,
    ASK_NAME,
    ASK_EMAIL,
    ASK_CONSENT
)

from django.utils import autoreload

@sync_to_async
def update_bot_status(is_running=True, error_message=""):
    """Update bot status in database"""
    from apps.bot.models import BotStatus
    status = BotStatus.get_status()
    status.is_running = is_running
    status.error_message = error_message
    status.last_heartbeat = timezone.now()
    if is_running and not status.started_at:
        status.started_at = timezone.now()
    status.save()

async def heartbeat_job(context):
    """Periodic job to update bot heartbeat"""
    try:
        await update_bot_status(is_running=True, error_message="")
    except Exception as e:
        logger.error(f"Failed to update heartbeat: {e}")

async def error_handler(update, context):
    """Global error handler for the bot"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Notify admins about the error
    try:
        from apps.bot.notifications import notify_admins_error
        error_details = f"{type(context.error).__name__}: {str(context.error)}"
        await notify_admins_error("Telegram Bot Error", error_details)
    except Exception as e:
        logger.error(f"Failed to notify admins about error: {e}")

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
                ASK_CONSENT: [CallbackQueryHandler(agreement_handler)],
            },
            fallbacks=[CommandHandler("start", start)],
        )

        app.add_handler(conv_handler)

        app.add_handler(CallbackQueryHandler(category_handler, pattern="^cat:"))
        app.add_handler(CallbackQueryHandler(document_handler, pattern="^doc:"))
        app.add_handler(CallbackQueryHandler(back_handler, pattern="^back$"))
        app.add_handler(CallbackQueryHandler(toggle_subscription_handler, pattern="^sub:toggle:"))
        app.add_handler(CallbackQueryHandler(initiate_search_handler, pattern="^search_init$"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_query))
        app.add_handler(CommandHandler("search", search_handler))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # Add heartbeat job (every 30 seconds)
        job_queue = app.job_queue
        job_queue.run_repeating(heartbeat_job, interval=30, first=0)
        
        # We'll use the job queue to handle the "started" status instead of asyncio.run
        # to avoid event loop conflicts in the management command.

        print("🤖 Telegram bot started")
        try:
            app.run_polling(close_loop=False)
        except Exception as e:
            logger.error(f"Bot stopped with error: {e}")
            # We can't easily run async code here if the loop is broken,
            # but usually the heartbeat will stop by itself.
            raise
