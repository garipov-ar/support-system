import httpx
from django.conf import settings
from apps.bot.models import BotUser
import logging

logger = logging.getLogger(__name__)

async def broadcast_notification(document_version):
    """
    Sends notification to all users subscribed to the document's category
    or any of its parent categories.
    """
    document = document_version.document
    category = document.category
    
    # Find all relevant categories (including ancestors)
    relevant_categories = category.get_ancestors(include_self=True)
    
    # Find all users subscribed to any of these categories
    subscribers = BotUser.objects.filter(
        subscribed_categories__in=relevant_categories,
        agreed_to_policy=True
    ).distinct()
    
    message_text = (
        f"🔔 *Обновление файлов!*\n\n"
        f"В разделе *{category.title}* доступен новый документ:\n"
        f"📄 *{document.title}* (v{document_version.version})\n\n"
        f"Вы получили это сообщение, так как подписаны на этот раздел."
    )
    
    # We use httpx directly to avoid heavy PTB dependencies in signals if possible,
    # or we can use the Bot instance. Let's use httpx for simplicity and async.
    token = settings.TELEGRAM_BOT_TOKEN
    base_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        for user in subscribers:
            try:
                await client.post(base_url, json={
                    "chat_id": user.telegram_id,
                    "text": message_text,
                    "parse_mode": "Markdown"
                })
            except Exception as e:
                logger.error(f"Failed to notify user {user.telegram_id}: {e}")
