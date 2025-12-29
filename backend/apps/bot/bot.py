from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import requests
import os

API_BASE = "http://web:8000/api"
MEDIA_ROOT = "/app/media"


async def build_root_keyboard():
    r = requests.get(f"{API_BASE}/navigation/")
    data = r.json()

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(c["title"], callback_data=f"cat:{c['id']}")]
        for c in data
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    for doc in data["documents"]:
        keyboard.append(
            [InlineKeyboardButton(
                f"📄 {doc['title']}",
                callback_data=f"doc:{doc['id']}|{doc['file_path']}"
            )]
        )

    keyboard.append(
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    )

    await query.edit_message_text(
        text=f"📂 {data['category']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, payload = query.data.split(":")
    _, file_path = payload.split("|")

    full_path = os.path.join(MEDIA_ROOT, file_path)

    with open(full_path, "rb") as f:
        await query.message.reply_document(
            document=f,
            filename=os.path.basename(full_path)
        )


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = await build_root_keyboard()

    await query.edit_message_text(
        text="Выберите раздел:",
        reply_markup=keyboard
    )
