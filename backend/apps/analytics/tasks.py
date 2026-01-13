from celery import shared_task
import asyncio
from asgiref.sync import async_to_sync
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_telegram_notification_task(chat_id, message, parse_mode='HTML'):
    """Async wrapper for sending Telegram notifications in background"""
    from apps.bot.notifications import send_telegram_notification
    try:
        async_to_sync(send_telegram_notification)(chat_id, message, parse_mode)
    except Exception as e:
        logger.error(f"Failed to send background notification to {chat_id}: {e}")

@shared_task
def create_audit_log_task(user_id=None, bot_user_id=None, action_type=None, object_type="", object_id=None, details=None, ip_address=None, user_agent=None):
    """Create audit log entry in background"""
    from apps.analytics.models import AuditLog
    from django.contrib.auth import get_user_model
    from apps.bot.models import BotUser
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id) if user_id else None
        bot_user = BotUser.objects.get(id=bot_user_id) if bot_user_id else None
        
        # Add user_agent to details if present
        if user_agent:
            if details is None:
                details = {}
            details['user_agent'] = user_agent
            
        AuditLog.objects.create(
            user=user,
            bot_user=bot_user,
            action_type=action_type,
            object_type=object_type,
            object_id=object_id,
            details=details or {},
            ip_address=ip_address
        )
    except Exception as e:
        logger.error(f"Failed to create background audit log: {e}")
