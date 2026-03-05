import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from django.utils.translation import gettext as _
from asgiref.sync import sync_to_async
from apps.bot.utils import is_user_subscribed, html_to_telegram

async def build_root_keyboard():
    from apps.content import services
    # Wrap in list to evaluate QuerySet in sync context
    categories = await sync_to_async(lambda: list(services.get_root_categories()))()

    keyboard = [
        [InlineKeyboardButton(f"🗂 {c.title}", callback_data=f"cat:{c.id}")]
        for c in categories
    ]
    keyboard.append([InlineKeyboardButton(_("🔍 Поиск"), callback_data="search_init")])
    keyboard.append([InlineKeyboardButton(_("📨 Написать администратору"), callback_data="support_start")])
    return InlineKeyboardMarkup(keyboard)

async def get_category_menu_content(data, user_id, prefix=""):
    category_id = data["id"]
    keyboard = []

    # Subcategories (data["subcategories"] is a list of dicts from service)
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

    # description
    description_text = ""
    if data.get("description"):
        clean_desc = html_to_telegram(data["description"])
        if clean_desc:
            description_text = f"\n\n{clean_desc}"

    text = f"{prefix}{status_icon} {safe_breadcrumbs}<u>{safe_title}</u>{description_text}"
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return text, reply_markup
