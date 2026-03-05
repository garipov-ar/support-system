import httpx
from django.conf import settings
from django.utils import timezone
from apps.bot.models import BotUser
import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

async def broadcast_notification(document_version):
    """
    Sends notification to all users subscribed to the document's category
    or any of its parent categories.
    """
    
    @sync_to_async
    def get_notification_data():
        document = document_version.content_node
        category = document.parent
        
        # Find all relevant categories (including ancestors)
        if category:
            relevant_categories = list(category.get_ancestors(include_self=True))
        else:
            relevant_categories = []
        
        # Find all users subscribed to any of these categories
        subscribers = list(BotUser.objects.filter(
            subscribed_categories__in=relevant_categories,
            agreed_to_policy=True
        ).distinct())
        
        return document, category, subscribers

    document, category, subscribers = await get_notification_data()
    
    message_text = (
        f"🔔 *Обновление файлов!*\n\n"
        f"В разделе *{category.title}* доступен новый документ:\n"
        f"📄 *{document.title}* (v{document_version.version})\n\n"
        f"Вы получили это сообщение, так как подписаны на этот раздел."
    )
    
    from apps.analytics.tasks import send_telegram_notification_task

    for user in subscribers:
        if user.telegram_id:
            send_telegram_notification_task.delay(user.telegram_id, message_text, parse_mode="Markdown")

@sync_to_async
def get_admin_notification_settings():
    """Get all admins who should receive notifications"""
    from apps.bot.models import AdminNotificationSettings
    return list(AdminNotificationSettings.objects.select_related('admin_user').all())

async def send_telegram_notification(telegram_id, message, parse_mode="HTML"):
    """Send a Telegram message to a specific user"""
    token = settings.TELEGRAM_BOT_TOKEN
    base_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(base_url, json={
                "chat_id": telegram_id,
                "text": message,
                "parse_mode": parse_mode
            })
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram notification to {telegram_id}: {e}")
        return False

async def notify_admins_error(error_type, details):
    """Notify admins about system errors"""
    settings_list = await get_admin_notification_settings()
    
    message = (
        f"🚨 <b>Ошибка в системе</b>\n\n"
        f"<b>Тип:</b> {error_type}\n"
        f"<b>Детали:</b> {details}\n"
        f"<b>Время:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    for settings_obj in settings_list:
        if settings_obj.notify_on_errors and settings_obj.telegram_id:
            await send_telegram_notification(settings_obj.telegram_id, message)

async def notify_admins_unauthorized_access(username, ip_address, details=""):
    """Notify admins about unauthorized access attempts"""
    settings_list = await get_admin_notification_settings()
    
    message = (
        f"⚠️ <b>Попытка несанкционированного доступа</b>\n\n"
        f"<b>Пользователь:</b> {username}\n"
        f"<b>IP адрес:</b> {ip_address}\n"
        f"<b>Детали:</b> {details}\n"
        f"<b>Время:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    from apps.analytics.tasks import send_telegram_notification_task
    for settings_obj in settings_list:
        if settings_obj.notify_on_unauthorized and settings_obj.telegram_id:
            send_telegram_notification_task.delay(settings_obj.telegram_id, message)

async def notify_admins_bot_down(error_message=""):
    """Notify admins that the bot has stopped working"""
    settings_list = await get_admin_notification_settings()
    
    message = (
        f"🔴 <b>Бот остановлен</b>\n\n"
        f"Telegram бот перестал отвечать.\n"
        f"<b>Ошибка:</b> {error_message}\n"
        f"<b>Время:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    from apps.analytics.tasks import send_telegram_notification_task
    for settings_obj in settings_list:
        if settings_obj.notify_on_bot_down and settings_obj.telegram_id:
            send_telegram_notification_task.delay(settings_obj.telegram_id, message)

async def notify_admins_document_error(document_title, error_details):
    """Notify admins about document processing errors"""
    settings_list = await get_admin_notification_settings()
    
    message = (
        f"📄 <b>Ошибка обработки документа</b>\n\n"
        f"<b>Документ:</b> {document_title}\n"
        f"<b>Ошибка:</b> {error_details}\n"
        f"<b>Время:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    for settings_obj in settings_list:
        if settings_obj.notify_on_errors and settings_obj.telegram_id:
            await send_telegram_notification(settings_obj.telegram_id, message)

async def notify_admins_storage_limit(total_size_bytes):
    """Notify admins that the storage limit (5GB) has been exceeded"""
    settings_list = await get_admin_notification_settings()
    
    try:
        gb_size = "%.2f" % (total_size_bytes / (1024 * 1024 * 1024))
    except (TypeError, ZeroDivisionError):
        gb_size = "5.00+"
        
    message = (
        f"⚠️ <b>Превышен лимит хранилища!</b>\n\n"
        f"Общий объем загруженных документов и файлов превысил <b>5 ГБ</b>.\n"
        f"Текущий объем: ~{gb_size} ГБ.\n"
        f"<b>Время:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    for settings_obj in settings_list:
        if settings_obj.notify_on_errors and settings_obj.telegram_id:
            await send_telegram_notification(settings_obj.telegram_id, message)

async def notify_admins_support_request(support_request):
    """Notify admins about a new support request from web or bot"""
    settings_list = await get_admin_notification_settings()
    
    django_user = getattr(support_request, 'django_user', None)
    bot_user = getattr(support_request, 'user', None)
    
    user_info = "Неизвестный пользователь"
    if django_user:
        user_info = f"{django_user.get_full_name() or django_user.username} (Web)"
    elif bot_user:
        user_info = f"{bot_user.first_name} {bot_user.last_name or ''} (@{bot_user.username or '??'}) (Bot)"
        
    message = (
        f"📩 <b>Новое обращение в поддержку!</b>\n\n"
        f"<b>От:</b> {user_info}\n"
        f"<b>Сообщение:</b>\n<i>{support_request.message}</i>\n\n"
        f"<b>Время:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    from apps.analytics.tasks import send_telegram_notification_task
    for settings_obj in settings_list:
        if settings_obj.telegram_id:
            send_telegram_notification_task.delay(settings_obj.telegram_id, message)

async def notify_admins_new_user(user, source="Web"):
    """Notify admins about a new user registration"""
    settings_list = await get_admin_notification_settings()
    
    message = (
        f"👤 <b>Новый пользователь!</b>\n\n"
        f"<b>Логин:</b> <code>{user.username}</code>\n"
        f"<b>Email:</b> {user.email}\n"
        f"<b>Имя:</b> {user.get_full_name() or '---'}\n"
        f"<b>Источник:</b> {source}\n\n"
        f"<b>Время:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    from apps.analytics.tasks import send_telegram_notification_task
    for settings_obj in settings_list:
        if settings_obj.telegram_id:
            send_telegram_notification_task.delay(settings_obj.telegram_id, message)
