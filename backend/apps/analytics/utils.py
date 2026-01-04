import time
import logging
from functools import wraps
from asgiref.sync import sync_to_async
from apps.analytics.models import BotInteraction, SearchQueryLog, AuditLog

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
            
            # Also create an AuditLog entry
            action_map = {
                'command': 'BOT_REQUEST',
                'callback': 'BOT_REQUEST',
                'download': 'FILE_DOWNLOAD',
                'search': 'BOT_REQUEST'
            }
            await create_audit_log(
                bot_user=user,
                action_type=action_map.get(action_type, 'BOT_REQUEST'),
                details={'path': path, 'duration': duration}
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
            
            # Also create an AuditLog entry
            await create_audit_log(
                bot_user=user,
                action_type='BOT_REQUEST',
                details={'query': query_text, 'results': results_count}
            )
    except Exception as e:
        logger.error(f"Failed to log search: {e}")

@sync_to_async
def create_audit_log(user=None, bot_user=None, action_type=None, object_type="", object_id=None, details=None, ip_address=None):
    """Creates an audit log entry. Can be called from sync or async contexts (via sync_to_async)."""
    return AuditLog.objects.create(
        user=user,
        bot_user=bot_user,
        action_type=action_type,
        object_type=object_type,
        object_id=object_id,
        details=details or {},
        ip_address=ip_address
    )
