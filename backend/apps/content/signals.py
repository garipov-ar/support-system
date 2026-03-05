from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Category, DocumentVersion
from apps.bot.notifications import broadcast_notification, notify_admins_document_error
from apps.analytics.utils import create_audit_log
from apps.analytics.middleware import get_current_user, get_current_ip
from asgiref.sync import async_to_sync
import asyncio
import threading

def run_async(coro):
    """Helper to run async code from sync Django signals"""
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_until_complete, args=(coro,)).start()

@receiver(post_save, sender=DocumentVersion)
def notify_subscribers(sender, instance, created, **kwargs):
    if created:
        try:
            # Run broadcast in a separate thread/event loop to not block the request
            run_async(broadcast_notification(instance))
            
            # Log version creation
            node_title = instance.content_node.title if instance.content_node else "Unknown"
            async_to_sync(create_audit_log)(
                user=get_current_user(),
                action_type='DOCUMENT_EDIT',
                object_type='Category',
                object_id=instance.content_node.id if instance.content_node else None,
                details={'version': instance.version, 'category_title': node_title},
                ip_address=get_current_ip()
            )
        except Exception as e:
            # Notify admins about processing error
            node_title = instance.content_node.title if instance.content_node else "Unknown"
            # Log the error
            async_to_sync(create_audit_log)(
                user=get_current_user(),
                action_type='BOT_REQUEST',
                details={'error': str(e), 'context': 'document_processing'}
            )

        # Storage Limit Check
        try:
            from django.core.cache import cache
            from django.db.models import Sum
            
            # Use cache to avoid recalculating and spamming notifications every single time
            # Only check once an hour or only if it hasn't alerted recently
            alert_cooldown_key = "storage_limit_alert_sent"
            if not cache.get(alert_cooldown_key):
                agg = DocumentVersion.objects.aggregate(total=Sum('file_size'))
                total_size_bytes = agg['total'] or 0
                limit_bytes = 5 * 1024 * 1024 * 1024 # 5 GB
                
                if total_size_bytes > limit_bytes:
                    from apps.bot.notifications import notify_admins_storage_limit
                    run_async(notify_admins_storage_limit(total_size_bytes))
                    # Prevent another notification for 24 hours
                    cache.set(alert_cooldown_key, True, timeout=86400)
        except Exception as cache_e:
            import logging
            logging.getLogger(__name__).error(f"Error checking storage limit: {cache_e}")

@receiver(post_delete, sender=DocumentVersion)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `DocumentVersion` object is deleted.
    """
    if instance.file:
        import os
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)



@receiver(post_save, sender=Category)
def log_category_save(sender, instance, created, **kwargs):
    # Invalidate Cache
    from django.core.cache import cache
    cache.delete("category_root")
    # If it's a child, invalidate parent
    if instance.parent:
        cache.delete(f"category_{instance.parent.id}_details")
    # Invalidate self
    cache.delete(f"category_{instance.id}_details")

    action = 'CATEGORY_CREATE' if created else 'CATEGORY_EDIT'
    async_to_sync(create_audit_log)(
        user=get_current_user(),
        action_type=action,
        object_type='Category',
        object_id=instance.id,
        details={'title': instance.title},
        ip_address=get_current_ip()
    )

@receiver(post_delete, sender=Category)
def log_category_delete(sender, instance, **kwargs):
    # Invalidate Cache
    from django.core.cache import cache
    cache.delete("category_root")
    if instance.parent:
        cache.delete(f"category_{instance.parent.id}_details")
    cache.delete(f"category_{instance.id}_details")

    async_to_sync(create_audit_log)(
        user=get_current_user(),
        action_type='CATEGORY_DELETE',
        object_type='Category',
        object_id=instance.id,
        details={'title': instance.title},
        ip_address=get_current_ip()
    )
