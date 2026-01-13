import time
import logging
from functools import wraps
from asgiref.sync import sync_to_async
from apps.analytics.models import BotInteraction, SearchQueryLog, AuditLog

logger = logging.getLogger(__name__)

async def log_interaction(user_id=None, action_type="unknown", path=None, duration=0, django_user=None):
    """Logs an interaction (Bot or Web) to the database asynchronously."""
    from apps.bot.models import BotUser
    try:
        user = None
        if user_id:
            user = await sync_to_async(BotUser.objects.filter(telegram_id=user_id).first)()
        
        if user or django_user:
            await sync_to_async(BotInteraction.objects.create)(
                user=user,
                django_user=django_user,
                action_type=action_type,
                path=path,
                response_time_ms=duration
            )
            
            # Also create an AuditLog entry (Optional for high-volume web views, but unified is good)
            # Only log detailed Audit for non-read actions or specific milestones? 
            # For now, let's skip explicit AuditLog for simple page views to avoid clutter, 
            # OR keep it consistency. Let's keep consistency for now but maybe filter in Admin.
            
            # Action Map
            action_map_key = action_type
            if action_type == 'web_view':
                 action_map_key = 'BOT_REQUEST' # Reuse generic request or add WEB_VIEW? 
                 # Let's map web_view to BOT_REQUEST for now or UNKNOWN
            
            action_map = {
                'command': 'BOT_REQUEST',
                'callback': 'BOT_REQUEST',
                'download': 'FILE_DOWNLOAD',
                'search': 'BOT_REQUEST',
                'web_view': 'BOT_REQUEST', # Treating web view as request
                'web_download': 'FILE_DOWNLOAD'
            }
            
            # Create Audit Log via Task
            await create_audit_log(
                bot_user=user,
                user=django_user,
                action_type=action_map.get(action_type, 'BOT_REQUEST'),
                details={'path': path, 'duration': duration, 'source': 'web' if django_user else 'bot'},
                ip_address='Web' if django_user else 'Telegram'
            )
    except Exception as e:
        logger.error(f"Failed to log interaction: {e}")

async def log_search_query(user_id=None, query_text="", results_count=0, django_user=None):
    """Logs a search query (Bot or Web) to the database asynchronously."""
    from apps.bot.models import BotUser
    try:
        user = None
        if user_id:
            user = await sync_to_async(BotUser.objects.filter(telegram_id=user_id).first)()
        
        if user or django_user:
            # Create SearchQueryLog entry
            await sync_to_async(SearchQueryLog.objects.create)(
                user=user,
                django_user=django_user,
                query_text=query_text,
                results_count=results_count
            )
            
            # Also create an AuditLog entry
            await create_audit_log(
                bot_user=user,
                user=django_user,
                action_type='BOT_REQUEST',
                details={'query': query_text, 'results': results_count, 'source': 'web' if django_user else 'bot'},
                ip_address='Web' if django_user else 'Telegram'
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
    bot_user_id = bot_user.id if bot_user and hasattr(bot_user, 'id') else None
    
    # We pass necessary data to the background task
    create_audit_log_task.delay(
        user_id=user_id,
        bot_user_id=bot_user_id,
        action_type=action_type,
        object_type=object_type,
        object_id=object_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
