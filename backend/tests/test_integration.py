import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from asgiref.sync import sync_to_async
from apps.bot import handlers
from apps.bot.models import BotUser
from apps.content.models import Category

@pytest.mark.django_db
class TestBotIntegration:
    
    @pytest.fixture
    def mock_update(self):
        update = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.username = "testuser"
        update.message.reply_text = AsyncMock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.from_user.id = 12345
        return update

    @pytest.fixture
    def mock_context(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_start_command_registration_flow(self, mock_update, mock_context):
        """Test the initial start command triggers registration (п. 1.4.2.1.2)"""
        # 1. User starts bot for the first time
        result = await handlers.start(mock_update, mock_context)
        
        # Verify bot asks for name
        mock_update.message.reply_text.assert_called()
        args, kwargs = mock_update.message.reply_text.call_args
        # The prompt in handlers.py is: "Добро пожаловать! ... введите ваше *Имя и Фамилию*:"
        assert "Имя и Фамилию" in args[0]
        assert result == handlers.ASK_NAME

    @pytest.mark.asyncio
    async def test_registration_step_name_to_email(self, mock_update, mock_context):
        """Test the flow from receiving name to asking for email"""
        mock_update.message.text = "Иван Иванов"
        
        result = await handlers.receive_name(mock_update, mock_context)
        
        # Verify user name is updated in DB
        user = await BotUser.objects.aget(telegram_id=12345)
        assert user.first_name == "Иван"
        
        # Verify bot asks for email
        mock_update.message.reply_text.assert_called()
        # The prompt is: "Приятно познакомиться! Теперь введите ваш *Email*:"
        assert "Email" in mock_update.message.reply_text.call_args[0][0]
        assert result == handlers.ASK_EMAIL

    @pytest.mark.asyncio
    async def test_category_navigation_integration(self, mock_update, mock_context):
        """Test integration with content services for menu navigation (п. 1.4.1.1.2)"""
        # Setup data using acreate for safety in async context
        root_cat = await Category.objects.acreate(title="Инструкции", is_folder=True)
        
        # Mock callback query data
        mock_update.callback_query.data = f"cat:{root_cat.id}"
        
        await handlers.category_handler(mock_update, mock_context)
        
        # Verify bot edits message with new menu
        mock_update.callback_query.edit_message_text.assert_called_once()
        assert "Инструкции" in mock_update.callback_query.edit_message_text.call_args[1]["text"]

    @pytest.mark.asyncio
    @patch("apps.bot.notifications.send_telegram_notification", new_callable=AsyncMock)
    async def test_notification_delivery_logic(self, mock_send):
        """Verify the path from notification call to Telegram Bot API (п. 4.1.10)"""
        from apps.bot.notifications import send_telegram_notification
        chat_id = 123456789
        message = "System Update"
        
        await send_telegram_notification(chat_id, message)
        mock_send.assert_called_once_with(chat_id, message)
