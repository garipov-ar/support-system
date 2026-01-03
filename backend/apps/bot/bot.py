from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import requests
import os
from asgiref.sync import sync_to_async
from apps.bot.models import BotUser

API_BASE = "http://web:8000/api"
MEDIA_ROOT = "/app/media"


async def build_root_keyboard():
    r = requests.get(f"{API_BASE}/navigation/")
    data = r.json()

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(c["title"], callback_data=f"cat:{c['id']}")]
        for c in data
    ])


@sync_to_async
def save_bot_user(user):
    BotUser.objects.get_or_create(
        telegram_id=user.id,
        defaults={
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # безопасный вызов ORM
    await save_bot_user(user)

    keyboard = await build_root_keyboard()

    await update.message.reply_text(
        "Выберите раздел:",
        reply_markup=keyboard
    )

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_id = query.data.split(":")[1]

    r = requests.get(f"{API_BASE}/category/{category_id}/")
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
    r = requests.get(f"{API_BASE}/document/{doc_id}/")
    doc_data = r.json()
    
    file_path = doc_data["file_path"]
    description = doc_data["description"]
    title = doc_data["title"]
    
    print(f"DEBUG: Processing doc {doc_id}")
    print(f"DEBUG: Description: '{description}'")
    print(f"DEBUG: Title: '{title}'")
    
    caption_text = description if description else title
    print(f"DEBUG: Final caption: '{caption_text}'")

    if file_path:
        full_path = os.path.join(MEDIA_ROOT, file_path)

        with open(full_path, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=os.path.basename(full_path),
                caption=description if description else title,
                parse_mode="HTML"
            )
    else:
        await query.message.reply_text("Файл не найден.")


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
    r = requests.get(f"{API_BASE}/search/", params={"q": query})
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
