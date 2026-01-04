import time
import logging
from functools import wraps
from asgiref.sync import sync_to_async
from apps.analytics.models import BotInteraction, SearchQueryLog

logger = logging.getLogger(__name__)

async def log_interaction(user_id, action_type, path=None, duration=0):
    """Logs a bot interaction to the database asynchronously."""
    from apps.bot.models import BotUser
    try:
        user = await sync_to_async(BotUser.objects.filter(telegram_id=user_id).first)()
        if user:
            await sync_to_async(BotInteraction.objects.create)(
                user=user,
                action_type=action_type,
                path=path,
                response_time_ms=duration
            )
    except Exception as e:
        logger.error(f"Failed to log interaction: {e}")

async def log_search_query(user_id, query_text, results_count):
    """Logs a search query to the database asynchronously."""
    from apps.bot.models import BotUser
    try:
        user = await sync_to_async(BotUser.objects.filter(telegram_id=user_id).first)()
        if user:
            await sync_to_async(SearchQueryLog.objects.create)(
                user=user,
                query_text=query_text,
                results_count=results_count
            )
    except Exception as e:
        logger.error(f"Failed to log search: {e}")
