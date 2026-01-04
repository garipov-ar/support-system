from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DocumentVersion
from apps.bot.notifications import broadcast_notification
import asyncio
import threading

def run_async(coro):
    """Helper to run async code from sync Django signals"""
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_until_complete, args=(coro,)).start()

@receiver(post_save, sender=DocumentVersion)
def notify_subscribers(sender, instance, created, **kwargs):
    if created:
        # Run broadcast in a separate thread/event loop to not block the request
        run_async(broadcast_notification(instance))
