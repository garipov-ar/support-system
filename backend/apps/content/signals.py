from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Document, Category, DocumentVersion
from apps.bot.notifications import broadcast_notification, notify_admins_document_error
from apps.analytics.utils import create_audit_log
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
            async_to_sync(create_audit_log)(
                action_type='DOCUMENT_EDIT',
                object_type='Document',
                object_id=instance.document.id,
                details={'version': instance.version, 'document_title': instance.document.title}
            )
        except Exception as e:
            # Notify admins about processing error
            run_async(notify_admins_document_error(instance.document.title, str(e)))
            # Log the error
            async_to_sync(create_audit_log)(
                action_type='BOT_REQUEST',
                details={'error': str(e), 'context': 'document_processing'}
            )

@receiver(post_save, sender=Document)
def log_document_save(sender, instance, created, **kwargs):
    action = 'DOCUMENT_CREATE' if created else 'DOCUMENT_EDIT'
    async_to_sync(create_audit_log)(
        action_type=action,
        object_type='Document',
        object_id=instance.id,
        details={'title': instance.title}
    )

@receiver(post_delete, sender=Document)
def log_document_delete(sender, instance, **kwargs):
    async_to_sync(create_audit_log)(
        action_type='DOCUMENT_DELETE',
        object_type='Document',
        object_id=instance.id,
        details={'title': instance.title}
    )

@receiver(post_save, sender=Category)
def log_category_save(sender, instance, created, **kwargs):
    action = 'CATEGORY_CREATE' if created else 'CATEGORY_EDIT'
    async_to_sync(create_audit_log)(
        action_type=action,
        object_type='Category',
        object_id=instance.id,
        details={'title': instance.title}
    )

@receiver(post_delete, sender=Category)
def log_category_delete(sender, instance, **kwargs):
    async_to_sync(create_audit_log)(
        action_type='CATEGORY_DELETE',
        object_type='Category',
        object_id=instance.id,
        details={'title': instance.title}
    )
