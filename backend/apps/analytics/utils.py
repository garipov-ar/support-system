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
def create_audit_log(user=None, bot_user=None, action_type=None, object_type="", object_id=None, details=None, ip_address=None, user_agent=None):
    """
    Helper function to create audit logs.
    Now calls a Celery task to perform the database write in the background.
    """
    from apps.analytics.tasks import create_audit_log_task
    user_id = user.id if user and hasattr(user, 'id') else None
    
    # We pass necessary data to the background task
    create_audit_log_task.delay(
        user_id=user_id,
        action=action_type,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
