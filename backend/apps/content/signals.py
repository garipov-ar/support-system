from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Document, Category, DocumentVersion
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
            run_async(notify_admins_document_error(node_title, str(e)))
            # Log the error
            async_to_sync(create_audit_log)(
                user=get_current_user(),
                action_type='BOT_REQUEST',
                details={'error': str(e), 'context': 'document_processing'}
            )

@receiver(post_save, sender=Document)
def log_document_save(sender, instance, created, **kwargs):
    action = 'DOCUMENT_CREATE' if created else 'DOCUMENT_EDIT'
    async_to_sync(create_audit_log)(
        user=get_current_user(),
        action_type=action,
        object_type='Document',
        object_id=instance.id,
        details={'title': instance.title},
        ip_address=get_current_ip()
    )

@receiver(post_delete, sender=Document)
def log_document_delete(sender, instance, **kwargs):
    async_to_sync(create_audit_log)(
        user=get_current_user(),
        action_type='DOCUMENT_DELETE',
        object_type='Document',
        object_id=instance.id,
        details={'title': instance.title},
        ip_address=get_current_ip()
    )

@receiver(post_save, sender=Category)
def log_category_save(sender, instance, created, **kwargs):
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
    async_to_sync(create_audit_log)(
        user=get_current_user(),
        action_type='CATEGORY_DELETE',
        object_type='Category',
        object_id=instance.id,
        details={'title': instance.title},
        ip_address=get_current_ip()
    )
