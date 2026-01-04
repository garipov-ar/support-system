from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .utils import create_audit_log
from asgiref.sync import async_to_sync

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    async_to_sync(create_audit_log)(
        user=user,
        action_type='LOGIN',
        ip_address=ip,
        details={'user_agent': request.META.get('HTTP_USER_AGENT')}
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    async_to_sync(create_audit_log)(
        user=user,
        action_type='LOGOUT',
        ip_address=ip
    )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    async_to_sync(create_audit_log)(
        action_type='UNAUTHORIZED_ACCESS',
        ip_address=ip,
        details={
            'attempted_username': credentials.get('username'),
            'user_agent': request.META.get('HTTP_USER_AGENT')
        }
    )
    
    # Notify admins about unauthorized access attempt
    from apps.bot.notifications import notify_admins_unauthorized_access
    import threading
    import asyncio
    
    def run_notify():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(notify_admins_unauthorized_access(
            username=credentials.get('username', 'Unknown'),
            ip_address=ip,
            details=f"Failed login attempt. User-Agent: {request.META.get('HTTP_USER_AGENT')}"
        ))
        loop.close()
    
    threading.Thread(target=run_notify).start()
