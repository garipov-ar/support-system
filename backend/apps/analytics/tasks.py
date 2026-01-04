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
def create_audit_log_task(user_id, action, details=None, ip_address=None, user_agent=None):
    """Create audit log entry in background"""
    from apps.analytics.models import AuditLog
    from django.contrib.auth.models import User
    try:
        user = User.objects.get(id=user_id) if user_id else None
        AuditLog.objects.create(
            user=user,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Failed to create background audit log: {e}")
