import os
import logging
import httpx
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import httpx
import os
import logging

logger = logging.getLogger(__name__)
from asgiref.sync import sync_to_async
from apps.bot.models import BotUser

API_BASE = "http://web:8000/api"
MEDIA_ROOT = "/app/media"


from django.utils.translation import gettext as _

async def build_root_keyboard():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/navigation/")
        data = r.json()

    keyboard = [
        [InlineKeyboardButton(f"🗂 {c['title']}", callback_data=f"cat:{c['id']}")]
        for c in data
    ]
    keyboard.append([InlineKeyboardButton(_("🔍 Поиск"), callback_data="search_init")])
    return InlineKeyboardMarkup(keyboard)


from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

ASK_NAME, ASK_EMAIL, ASK_CONSENT = range(3)

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
    # Пытаемся разбить на имя/фамилию, если возможно
    parts = full_name.split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    
    BotUser.objects.filter(telegram_id=telegram_id).update(
        first_name=first_name,
        last_name=last_name
    )

@sync_to_async
def update_user_email(telegram_id, email):
    BotUser.objects.filter(telegram_id=telegram_id).update(email=email)

@sync_to_async
def update_user_agreement(telegram_id):
    BotUser.objects.filter(telegram_id=telegram_id).update(agreed_to_policy=True)

@sync_to_async
def is_user_subscribed(telegram_id, category_id):
    from apps.content.models import Category
    user = BotUser.objects.filter(telegram_id=telegram_id).prefetch_related('subscribed_categories').first()
    if user:
        # Check direct subscription
        if user.subscribed_categories.filter(id=category_id).exists():
            return True, "direct"
        
        # Check inherited subscription (from parents)
        try:
            category = Category.objects.get(id=category_id)
            ancestors = category.get_ancestors()
            if user.subscribed_categories.filter(id__in=ancestors).exists():
                return True, "inherited"
        except Category.DoesNotExist:
            pass
            
    return False, None

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    user = update.effective_user
    
    # 1. Создаем запись если нет (чтобы не было ошибок), но не сохраняем имя из телеграма
    await create_initial_user(user)

    db_user = await get_bot_user(user.id)
    
    from apps.analytics.utils import log_interaction
    
    # Если уже согласился - сразу меню
    if db_user.agreed_to_policy:
        keyboard = await build_root_keyboard()
        await update.message.reply_text(_("Выберите раздел:"), reply_markup=keyboard)
        
        duration = int((time.time() - start_time) * 1000)
        await log_interaction(user.id, "command", "/start", duration=duration)
        return ConversationHandler.END

    # Иначе начинаем регистрацию
    await update.message.reply_text(
        _("Добро пожаловать! Для начала работы нам нужно познакомиться.\n"
        "Пожалуйста, введите ваше *Имя и Фамилию*:"),
        parse_mode="Markdown"
    )
    
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(user.id, "command", "/start_reg", duration=duration)
    return ASK_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if len(name) < 2:
        await update.message.reply_text(_("Слишком короткое имя. Пожалуйста, введите *Имя и Фамилию*:"), parse_mode="Markdown")
        return ASK_NAME
        
    await update_user_name(update.effective_user.id, name)
    
    await update.message.reply_text(_("Приятно познакомиться! Теперь введите ваш *Email*:"), parse_mode="Markdown")
    return ASK_EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    if "@" not in email:
        await update.message.reply_text(_("Некорректный email. Попробуйте еще раз:"))
        return ASK_EMAIL
        
    await update_user_email(update.effective_user.id, email)
    
    # Показываем соглашение
    keyboard = [
        [InlineKeyboardButton(_("✅ Согласен на обработку данных"), callback_data="agree_policy")]
    ]
    await update.message.reply_text(
        _("Остался последний шаг. Для использования бота необходимо дать согласие на обработку персональных данных."),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_CONSENT


async def agreement_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "agree_policy":
        await update_user_agreement(query.from_user.id)
        
        keyboard = await build_root_keyboard()
        
        await query.edit_message_text(
            text=_("Спасибо! Вы успешно зарегистрированы.\nВыберите раздел:"),
            reply_markup=keyboard
        )
        return ConversationHandler.END
    return ASK_CONSENT # Should not happen usually

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_("Регистрация прервана. Напишите /start чтобы начать заново."))
    return ConversationHandler.END

import html

async def get_category_menu_content(data, user_id, prefix=""):
    category_id = data["id"]
    keyboard = []

    # Subcategories
    for sub in data.get("subcategories", []):
         keyboard.append(
            [InlineKeyboardButton(
                f"📂 {sub['title']}",
                callback_data=f"cat:{sub['id']}"
            )]
        )

    # Documents
    for doc in data["documents"]:
        keyboard.append(
            [InlineKeyboardButton(
                f"📄 {doc['title']}",
                callback_data=f"doc:{doc['id']}"
            )]
        )

    # Subscription button
    is_subbed, sub_type = await is_user_subscribed(user_id, category_id)
    
    if sub_type == "inherited":
        sub_text = "🔕"
    else:
        sub_text = "🔕" if is_subbed else "🔔"
    
    keyboard.append(
        [InlineKeyboardButton(sub_text, callback_data=f"sub:toggle:{category_id}")]
    )

    # Search button
    keyboard.append(
        [InlineKeyboardButton(_("🔍 Поиск по разделу"), callback_data="search_init")]
    )


    # Back button
    parent_id = data.get("parent_id")
    if parent_id:
        back_callback = f"cat:{parent_id}"
    else:
        back_callback = "back"

    keyboard.append(
        [InlineKeyboardButton(_("⬅ Назад"), callback_data=back_callback)]
    )

    # Clearer status indicator
    status_icon = "🗂" if parent_id is None else "📂"

    # Breadcrumbs
    path_list = data.get("path", [])
    breadcrumbs = ""
    if path_list:
        breadcrumbs = " > ".join(path_list) + " > "
    
    # Escape for HTML
    safe_title = html.escape(str(data['category']))
    safe_breadcrumbs = html.escape(breadcrumbs)

    # prefix is assumed to be HTML if it has tags, but for now we keep it simple
    text = f"{prefix}{status_icon} {safe_breadcrumbs}<u>{safe_title}</u>"
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return text, reply_markup


async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, category_id=None, answer=True, prefix=""):
    start_time = time.time()
    query = update.callback_query
    if query and answer:
        await query.answer()

    if category_id is None:
        # data format: "cat:<id>" or "sub:toggle:<id>"
        parts = query.data.split(":")
        category_id = parts[-1]
    
    # Ensure category_id is a string and not empty/invalid
    category_id = str(category_id)
    if not category_id or not category_id.isdigit():
        logger.error(f"Invalid category_id: '{category_id}' from query data: '{query.data if query else 'N/A'}'")
        if query:
            await query.edit_message_text("Ошибка: неверный ID категории.")
        return

    url = f"{API_BASE}/category/{category_id}/"
    logger.info(f"Requesting category data: {url}")

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url)
            if r.status_code != 200:
                logger.error(f"API Error {r.status_code} for {url}: {r.text}")
                if query:
                    await query.edit_message_text(_("Ошибка загрузки категории (API)."))
                return
            data = r.json()
        except Exception as e:
            logger.error(f"Request/JSON Error for {url}: {e}")
            if query:
                await query.edit_message_text(_("Произошла системная ошибка при загрузке данных."))
            return

    text, reply_markup = await get_category_menu_content(data, query.from_user.id, prefix=prefix)

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    from apps.analytics.utils import log_interaction
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(query.from_user.id, "callback", f"cat:{category_id}", duration=duration)


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    query = update.callback_query
    await query.answer()

    doc_id = query.data.split(":")[1]
    
    # Fetch document details
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/document/{doc_id}/")
        doc_data = r.json()
    
    file_path = doc_data["file_path"]
    description = doc_data["description"]
    title = doc_data["title"]
    category_id = doc_data["category_id"]
    
    version = doc_data.get("version")
    equipment_name = doc_data.get("equipment_name")

    caption_parts = []
    caption_parts.append(title)
    if version:
        caption_parts.append(f"<b>Версия:</b> {version}")
    if equipment_name:
        caption_parts.append(f"<b>Оборудование:</b> {equipment_name}")
    
    if description:
        caption_parts.append(f"\n<i>{description}</i>")
    
    caption = "\n".join(caption_parts)

    # 1. Отправляем файл
    if file_path:
        full_path = os.path.join(MEDIA_ROOT, file_path)
        ext = os.path.splitext(full_path)[1].lower()

        with open(full_path, "rb") as f:
            if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                await query.message.reply_photo(
                    photo=f,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                await query.message.reply_document(
                    document=f,
                    filename=os.path.basename(full_path),
                    caption=caption,
                    parse_mode="HTML"
                )
    else:
        await query.message.reply_text(_("Файл не найден."))

    # 2. Восстанавливаем меню (чтобы оно было снизу)
    try:
        await query.message.delete()
    except Exception:
        pass # Если не удалось удалить, не страшно

    # Получаем данные категории заново
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/category/{category_id}/")
        cat_data = r.json()

    text, reply_markup = await get_category_menu_content(cat_data, query.from_user.id)

    await query.message.reply_text(
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    from apps.analytics.utils import log_interaction
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(query.from_user.id, "callback", f"doc:{doc_id}", duration=duration)


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # We only handle back here. 
    # Back to parent category is handled by cat:<id> in category_handler
    if query.data == "back":
        keyboard = await build_root_keyboard()

        await query.edit_message_text(
            text="Выберите раздел:",
            reply_markup=keyboard
        )

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    if not context.args:
        await update.message.reply_text("Использование: /search <текст>")
        return

    query_text = " ".join(context.args)
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{API_BASE}/search/", params={"q": query_text})
            data = r.json()
        except Exception as e:
            logger.error(f"Search API error: {e}")
            await update.message.reply_text("Произошла ошибка при поиске.")
            return

    from apps.analytics.utils import log_search_query, log_interaction
    
    if not data:
        await update.message.reply_text(_("По запросу \"{query}\" ничего не найдено.").format(query=query_text))
        await log_search_query(update.effective_user.id, query_text, 0)
        duration = int((time.time() - start_time) * 1000)
        await log_interaction(update.effective_user.id, "command", "/search", duration=duration)
        return

    keyboard = []
    for item in data:
        keyboard.append([InlineKeyboardButton(f"📄 {item['title']}", callback_data=f"doc:{item['id']}")])
    
    # Back to root button
    keyboard.append([InlineKeyboardButton(_("🔙 В главное меню"), callback_data="back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🔍 Результаты поиска по запросу \"{query_text}\":",
        reply_markup=reply_markup
    )
    
    await log_search_query(update.effective_user.id, query_text, len(data))
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(update.effective_user.id, "command", "/search", duration=duration)

async def initiate_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for search button click - prompts user to enter search query"""
    query = update.callback_query
    await query.answer()
    
    # Set a flag in context to indicate we're waiting for search input
    context.user_data['awaiting_search'] = True
    
    await query.edit_message_text(
        _("🔍 Введите поисковый запрос:\n\n"
        "Я найду документы по названию и описанию."),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(_("❌ Отмена"), callback_data="back")
        ]])
    )

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for text messages when user is in search mode"""
    # Check if we're waiting for search input
    if not context.user_data.get('awaiting_search'):
        return  # Ignore text if not in search mode
    
    # Clear the flag
    context.user_data['awaiting_search'] = False
    
    start_time = time.time()
    query_text = update.message.text.strip()
    
    if not query_text:
        await update.message.reply_text(_("Пожалуйста, введите непустой запрос."))
        return
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{API_BASE}/search/", params={"q": query_text})
            data = r.json()
        except Exception as e:
            logger.error(f"Search API error: {e}")
            await update.message.reply_text("Произошла ошибка при поиске.")
            return

    from apps.analytics.utils import log_search_query, log_interaction
    
    if not data:
        await update.message.reply_text(
            _("По запросу \"{query}\" ничего не найдено.").format(query=query_text),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(_("🔙 В главное меню"), callback_data="back")
            ]])
        )
        await log_search_query(update.effective_user.id, query_text, 0)
        duration = int((time.time() - start_time) * 1000)
        await log_interaction(update.effective_user.id, "text_search", query_text, duration=duration)
        return

    keyboard = []
    for item in data:
        keyboard.append([InlineKeyboardButton(f"📄 {item['title']}", callback_data=f"doc:{item['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🔍 Результаты поиска по запросу \"{query_text}\":",
        reply_markup=reply_markup
    )
    
    await log_search_query(update.effective_user.id, query_text, len(data))
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(update.effective_user.id, "text_search", query_text, duration=duration)

async def toggle_subscription_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    query = update.callback_query

    # sub:toggle:<id>
    category_id = int(query.data.split(":")[2])
    
    is_subbed, sub_type = await is_user_subscribed(query.from_user.id, category_id)
    
    if sub_type == "inherited":
        await query.answer(_("Вы подписаны через родительскую категорию. Чтобы отписаться, перейдите в родительский раздел."), show_alert=True)
        return

    is_now_subbed = await toggle_subscription(query.from_user.id, category_id)
    
    # Send a quick toast answer
    await query.answer()

    if is_now_subbed:
        prefix = _("✅ <b>Вы успешно подписались!</b>\n\n")
    else:
        prefix = _("❌ <b>Вы отписались от обновлений.</b>\n\n")
    
    # Refresh the category menu with the success message
    await category_handler(update, context, category_id=category_id, answer=False, prefix=prefix)
    
    from apps.analytics.utils import log_interaction
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(query.from_user.id, "callback", f"sub:toggle:{category_id}", duration=duration)
