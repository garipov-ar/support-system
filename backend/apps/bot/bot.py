from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import httpx
import os
from asgiref.sync import sync_to_async
from apps.bot.models import BotUser

API_BASE = "http://web:8000/api"
MEDIA_ROOT = "/app/media"


async def build_root_keyboard():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/navigation/")
        data = r.json()

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(c["title"], callback_data=f"cat:{c['id']}")]
        for c in data
    ])


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Создаем запись если нет (чтобы не было ошибок), но не сохраняем имя из телеграма
    await create_initial_user(user)

    db_user = await get_bot_user(user.id)
    
    # Если уже согласился - сразу меню
    if db_user.agreed_to_policy:
        keyboard = await build_root_keyboard()
        await update.message.reply_text("Выберите раздел:", reply_markup=keyboard)
        return ConversationHandler.END

    # Иначе начинаем регистрацию
    await update.message.reply_text(
        "Добро пожаловать! Для начала работы нам нужно познакомиться.\n"
        "Пожалуйста, введите ваше *Имя и Фамилию*:",
        parse_mode="Markdown"
    )
    return ASK_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if len(name) < 2:
        await update.message.reply_text("Слишком короткое имя. Пожалуйста, введите *Имя и Фамилию*:", parse_mode="Markdown")
        return ASK_NAME
        
    await update_user_name(update.effective_user.id, name)
    
    await update.message.reply_text("Приятно познакомиться! Теперь введите ваш *Email*:", parse_mode="Markdown")
    return ASK_EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    if "@" not in email:
        await update.message.reply_text("Некорректный email. Попробуйте еще раз:")
        return ASK_EMAIL
        
    await update_user_email(update.effective_user.id, email)
    
    # Показываем соглашение
    keyboard = [
        [InlineKeyboardButton("✅ Согласен на обработку данных", callback_data="agree_policy")]
    ]
    await update.message.reply_text(
        "Остался последний шаг. Для использования бота необходимо дать согласие на обработку персональных данных.",
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
            text="Спасибо! Вы успешно зарегистрированы.\nВыберите раздел:",
            reply_markup=keyboard
        )
        return ConversationHandler.END
    return ASK_CONSENT # Should not happen usually

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Регистрация прервана. Напишите /start чтобы начать заново.")
    return ConversationHandler.END

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_id = query.data.split(":")[1]

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/category/{category_id}/")
        data = r.json()

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

    # Back button
    parent_id = data.get("parent_id")
    if parent_id:
        back_callback = f"cat:{parent_id}"
    else:
        back_callback = "back"

    keyboard.append(
        [InlineKeyboardButton("⬅ Назад", callback_data=back_callback)]
    )

    await query.edit_message_text(
        text=f"📂 {data['category']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    doc_id = query.data.split(":")[1]
    
    # Fetch document details
    # Fetch document details
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/document/{doc_id}/")
        doc_data = r.json()
    
    file_path = doc_data["file_path"]
    description = doc_data["description"]
    title = doc_data["title"]
    category_id = doc_data["category_id"]

    # 1. Отправляем файл
    if file_path:
        full_path = os.path.join(MEDIA_ROOT, file_path)
        ext = os.path.splitext(full_path)[1].lower()

        with open(full_path, "rb") as f:
            if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                await query.message.reply_photo(
                    photo=f,
                    caption=description if description else title,
                    parse_mode="HTML"
                )
            else:
                await query.message.reply_document(
                    document=f,
                    filename=os.path.basename(full_path),
                    caption=description if description else title,
                    parse_mode="HTML"
                )
    else:
        await query.message.reply_text("Файл не найден.")

    # 2. Восстанавливаем меню (чтобы оно было снизу)
    # Удаляем старое меню (опционально, чтобы не засорять чат)
    try:
        await query.message.delete()
    except Exception:
        pass # Если не удалось удалить, не страшно

    # Получаем данные категории заново
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/category/{category_id}/")
        cat_data = r.json()

    keyboard = []
    # Subcategories
    for sub in cat_data.get("subcategories", []):
         keyboard.append(
            [InlineKeyboardButton(
                f"📂 {sub['title']}",
                callback_data=f"cat:{sub['id']}"
            )]
        )

    # Documents
    for doc in cat_data["documents"]:
        keyboard.append(
            [InlineKeyboardButton(
                f"📄 {doc['title']}",
                callback_data=f"doc:{doc['id']}"
            )]
        )

    # Back button
    parent_id = cat_data.get("parent_id")
    if parent_id:
        back_callback = f"cat:{parent_id}"
    else:
        back_callback = "back"

    keyboard.append(
        [InlineKeyboardButton("⬅ Назад", callback_data=back_callback)]
    )

    await query.message.reply_text(
        text=f"📂 {cat_data['category']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


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
    if not context.args:
        await update.message.reply_text("Использование: /search <текст>")
        return

    query = " ".join(context.args)
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/search/", params={"q": query})
        data = r.json()

    if not data:
        await update.message.reply_text("Ничего не найдено")
        return

    for item in data:
        file_path = item["file_path"]
        full_path = os.path.join(MEDIA_ROOT, file_path)

        with open(full_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(full_path),
                caption=item["title"]
            )
