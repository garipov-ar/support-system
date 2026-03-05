import logging
from asgiref.sync import sync_to_async
from apps.bot.models import BotUser, SupportRequest, AdminNotificationSettings

logger = logging.getLogger(__name__)

@sync_to_async
def get_bot_user(telegram_id):
    try:
        return BotUser.objects.get(telegram_id=telegram_id)
    except BotUser.DoesNotExist:
        return None

@sync_to_async
def create_initial_user(user):
    BotUser.objects.get_or_create(
        telegram_id=user.id,
        defaults={
            "username": user.username,
        }
    )

@sync_to_async
def update_user_name(telegram_id, full_name):
    parts = full_name.split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    
    BotUser.objects.filter(telegram_id=telegram_id).update(
        first_name=first_name,
        last_name=last_name
    )

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

@sync_to_async
def update_user_email(telegram_id, email):
    bot_user = BotUser.objects.filter(telegram_id=telegram_id).first()
    if not bot_user:
        return None
        
    bot_user.email = email
    bot_user.save(update_fields=['email'])
    
    # Try to link with a Django User account
    User = get_user_model()
    try:
        django_user = User.objects.get(email__iexact=email)
        django_user.telegram_id = telegram_id
        django_user.save(update_fields=['telegram_id'])
        return None
    except User.DoesNotExist:
        # Create new web user
        password = get_random_string(length=10)
        
        base_username = email.split('@')[0]
        # Ensure username uniqueness by appending telegram_id
        username = f"{base_username}_{telegram_id}"
        
        new_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=bot_user.first_name or "",
            last_name=bot_user.last_name or "",
            telegram_id=telegram_id
        )
        return password
    except User.MultipleObjectsReturned:
        logger.warning(f"Multiple web users found for email {email}. Cannot link telegram ID automatically.")
        return None

@sync_to_async
def update_user_agreement(telegram_id):
    BotUser.objects.filter(telegram_id=telegram_id).update(agreed_to_policy=True)

@sync_to_async
def is_user_subscribed(telegram_id, category_id):
    from apps.content.models import Category
    user = BotUser.objects.filter(telegram_id=telegram_id).prefetch_related('subscribed_categories').first()
    if user:
        if user.subscribed_categories.filter(id=category_id).exists():
            return True, "direct"
        
        try:
            category = Category.objects.get(id=category_id)
            ancestors = category.get_ancestors()
            if user.subscribed_categories.filter(id__in=ancestors).exists():
                return True, "inherited"
        except Category.DoesNotExist:
            pass
            
    return False, None

@sync_to_async
def save_file_id_safe(document_id, file_id):
    from apps.content.models import Category, DocumentVersion
    try:
        node = Category.objects.get(id=document_id)
        version = DocumentVersion.objects.filter(content_node=node).order_by("-created_at").first()
        if version:
            version.telegram_file_id = file_id
            version.save()
    except Exception as e:
        logger.error(f"Error saving file_id: {e}") 

@sync_to_async
def toggle_subscription(telegram_id, category_id):
    from apps.content.models import Category
    user = BotUser.objects.get(telegram_id=telegram_id)
    category = Category.objects.get(id=category_id)
    if user.subscribed_categories.filter(id=category_id).exists():
        user.subscribed_categories.remove(category)
        return False
    else:
        user.subscribed_categories.add(category)
        return True

@sync_to_async
def save_support_request(telegram_id, message):
    user = BotUser.objects.filter(telegram_id=telegram_id).first()
    if user:
        SupportRequest.objects.create(user=user, message=message)
    return user

async def notify_admins(app, message, user_info):
    admins = await sync_to_async(lambda: list(AdminNotificationSettings.objects.filter(telegram_id__isnull=False)))()
    
    for admin in admins:
        try:
            text = f"📨 <b>Новое обращение в поддержку!</b>\n\nОт: {user_info}\n\nСообщение:\n<i>{message}</i>"
            await app.bot.send_message(chat_id=admin.telegram_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin.telegram_id}: {e}")
