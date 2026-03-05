import os
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, ConversationHandler
from django.utils.translation import gettext as _
from asgiref.sync import sync_to_async

from apps.bot.constants import ASK_NAME, ASK_EMAIL, ASK_CONSENT, ASK_SUPPORT_MESSAGE
from apps.bot.utils import (
    get_bot_user, create_initial_user, update_user_name, update_user_email,
    update_user_agreement, is_user_subscribed, save_file_id_safe,
    toggle_subscription, save_support_request, notify_admins
)
from apps.bot.keyboards import build_root_keyboard, get_category_menu_content
from apps.analytics.utils import log_interaction, log_search_query

logger = logging.getLogger(__name__)

# Import settings to access MEDIA_ROOT
from django.conf import settings
MEDIA_ROOT = settings.MEDIA_ROOT

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    user = update.effective_user
    
    # 1. Создаем запись если нет (чтобы не было ошибок), но не сохраняем имя из телеграма
    await create_initial_user(user)

    db_user = await get_bot_user(user.id)
    
    # Если уже согласился - сразу меню
    if db_user and db_user.agreed_to_policy:
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
        
    result = await update_user_email(update.effective_user.id, email)
    
    # result might be (username, password) or None
    username = None
    password = None
    if isinstance(result, tuple):
        username, password = result
    
    # Показываем соглашение
    keyboard = [
        [InlineKeyboardButton(_("✅ Согласен на обработку данных"), callback_data="agree_policy")]
    ]
    
    message_text = _("Остался последний шаг. Для использования бота необходимо дать согласие на обработку персональных данных.")
    
    if username and password:
        message_text = (
            f"Успешно! Для вас был автоматически создан аккаунт на сайте!\n\n"
            f"<b>Ваш логин:</b> <code>{username}</code>\n"
            f"<b>Ваш пароль:</b> <code>{password}</code>\n\n"
            f"Сохраните эти данные для входа в веб-панель.\n\n" + message_text
        )
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    return ASK_CONSENT

async def agreement_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "agree_policy":
        await update_user_agreement(query.from_user.id)
        
        keyboard = await build_root_keyboard()
        
        # Remove the inline keyboard from the password/consent message
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as e:
            logger.error(f"Failed to remove reply_markup on consent message: {e}")
            
        # Send the main menu as a new message
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_("Спасибо! Вы успешно зарегистрированы.\nВыберите раздел:"),
            reply_markup=keyboard
        )
        return ConversationHandler.END
    return ASK_CONSENT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_("Регистрация прервана. Напишите /start чтобы начать заново."))
    return ConversationHandler.END

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

    logger.info(f"Requesting category data for: {category_id}")

    from apps.content import services
    try:
        data = await sync_to_async(services.get_category_details)(category_id)
    except Exception as e:
        logger.error(f"Error fetching category {category_id}: {e}")
        if query:
            await query.edit_message_text(_("Ошибка загрузки категории."))
        return

    text, reply_markup = await get_category_menu_content(data, query.from_user.id, prefix=prefix)

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(query.from_user.id, "callback", f"cat:{category_id}", duration=duration)

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    query = update.callback_query
    await query.answer()

    doc_id = query.data.split(":")[1]
    
    # Fetch document details
    from apps.content import services
    try:
        doc_data = await sync_to_async(services.get_document_details)(doc_id)
    except Exception as e:
        logger.error(f"Error fetching document {doc_id}: {e}")
        await query.message.reply_text(_("Ошибка загрузки документа."))
        return
    
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

    telegram_file_id = doc_data.get("telegram_file_id")

    # 1. Отправляем файл
    sent_msg = None
    if telegram_file_id:
        try:
            sent_msg = await query.message.reply_document(
                document=telegram_file_id,
                caption=caption,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send by file_id: {e}")
            telegram_file_id = None

    if not telegram_file_id and file_path:
        full_path = os.path.join(MEDIA_ROOT, file_path)
        ext = os.path.splitext(full_path)[1].lower()

        if os.path.exists(full_path):
            with open(full_path, "rb") as f:
                if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                   sent_msg = await query.message.reply_photo(
                        photo=f,
                        caption=caption,
                        parse_mode="HTML"
                    )
                else:
                    sent_msg = await query.message.reply_document(
                        document=f,
                        filename=os.path.basename(full_path),
                        caption=caption,
                        parse_mode="HTML"
                    )
            
            # Save file_id for future use
            if sent_msg:
                new_file_id = None
                if sent_msg.document:
                    new_file_id = sent_msg.document.file_id
                elif sent_msg.photo:
                    new_file_id = sent_msg.photo[-1].file_id
                
                if new_file_id:
                     await save_file_id_safe(doc_id, new_file_id)

        else:
            await query.message.reply_text(_("Файл не найден на сервере."))
    elif not telegram_file_id and not file_path:
         await query.message.reply_text(_("Файл не прикреплен."))

    # 2. Восстанавливаем меню (чтобы оно было снизу)
    try:
        await query.message.delete()
    except Exception:
        pass 

    # Получаем данные категории заново
    from apps.content import services
    try:
        cat_data = await sync_to_async(services.get_category_details)(category_id)
    except Exception as e:
         logger.error(f"Error re-fetching category {category_id}: {e}")
         return

    text, reply_markup = await get_category_menu_content(cat_data, query.from_user.id)

    await query.message.reply_text(
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(query.from_user.id, "callback", f"doc:{doc_id}", duration=duration)

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
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
    
    from apps.content import services
    try:
        data = await sync_to_async(services.search_content)(query_text)
    except Exception as e:
        logger.error(f"Search Error: {e}")
        await update.message.reply_text("Произошла ошибка при поиске.")
        return

    if not data:
        await update.message.reply_text(_("По запросу \"{query}\" ничего не найдено.").format(query=query_text))
        await log_search_query(update.effective_user.id, query_text, 0)
        duration = int((time.time() - start_time) * 1000)
        await log_interaction(update.effective_user.id, "command", "/search", duration=duration)
        return

    keyboard = []
    for item in data:
        keyboard.append([InlineKeyboardButton(f"📄 {item['title']}", callback_data=f"doc:{item['id']}")])
    
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
    query = update.callback_query
    await query.answer()
    
    context.user_data['awaiting_search'] = True
    
    await query.edit_message_text(
        _("🔍 Введите поисковый запрос:\n\n"
        "Я найду документы по названию и описанию."),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(_("❌ Отмена"), callback_data="back")
        ]])
    )

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_search'):
        return
    
    context.user_data['awaiting_search'] = False
    
    start_time = time.time()
    query_text = update.message.text.strip()
    
    if not query_text:
        await update.message.reply_text(_("Пожалуйста, введите непустой запрос."))
        return
    
    from apps.content import services
    try:
        data = await sync_to_async(services.search_content)(query_text)
    except Exception as e:
        logger.error(f"Search Error: {e}")
        await update.message.reply_text("Произошла ошибка при поиске.")
        return

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

    category_id = int(query.data.split(":")[2])
    
    is_subbed, sub_type = await is_user_subscribed(query.from_user.id, category_id)
    
    if sub_type == "inherited":
        await query.answer(_("Вы подписаны через родительскую категорию. Чтобы отписаться, перейдите в родительский раздел."), show_alert=True)
        return

    is_now_subbed = await toggle_subscription(query.from_user.id, category_id)
    
    await query.answer()

    if is_now_subbed:
        prefix = _("✅ <b>Вы успешно подписались!</b>\n\n")
    else:
        prefix = _("❌ <b>Вы отписались от обновлений.</b>\n\n")
    
    await category_handler(update, context, category_id=category_id, answer=False, prefix=prefix)
    
    duration = int((time.time() - start_time) * 1000)
    await log_interaction(query.from_user.id, "callback", f"sub:toggle:{category_id}", duration=duration)

async def start_support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            _("Опишите вашу проблему или вопрос в одном сообщении:"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("❌ Отмена"), callback_data="back")]])
        )
    return ASK_SUPPORT_MESSAGE

async def receive_support_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    
    # Save to DB
    db_user = await save_support_request(user.id, text)
    
    # Notify Admins
    user_info = f"{user.first_name} (@{user.username})" if user.username else f"{user.first_name}"
    await notify_admins(context.application, text, user_info)
    
    # Log interaction
    await log_interaction(user.id, "support_request", "text", duration=0)

    # Reply to user
    await update.message.reply_text(
        _("✅ Ваше сообщение отправлено администратору. Мы свяжемся с вами в ближайшее время."),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("🔙 В главное меню"), callback_data="back")]])
    )
    return ConversationHandler.END
