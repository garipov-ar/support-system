import pytest
from apps.bot import utils as bot_utils
from apps.bot.models import BotUser
from apps.content.models import Category
from asgiref.sync import sync_to_async

@pytest.mark.django_db(transaction=True)
class TestBotUnitLogic:
    
    @pytest.mark.asyncio
    async def test_update_user_name_logic(self):
        """Test splitting of full name into first and last names (п. 4.1.2)"""
        # Create data inside the test with acreate to ensure visibility
        user = await BotUser.objects.acreate(telegram_id=999, username="test_bot_user")
        
        await bot_utils.update_user_name(999, "Иван Иванов")
        
        # Get user again
        updated_user = await bot_utils.get_bot_user(999)
        assert updated_user is not None
        assert updated_user.first_name == "Иван"
        assert updated_user.last_name == "Иванов"
        
        await bot_utils.update_user_name(999, "Петр")
        updated_user = await bot_utils.get_bot_user(999)
        assert updated_user.first_name == "Петр"
        assert updated_user.last_name == ""

    @pytest.mark.asyncio
    async def test_subscription_inheritance_logic(self):
        """Test if user is considered subscribed to a child if subscribed to parent"""
        # Create data inside the test
        user = await BotUser.objects.acreate(telegram_id=999, username="test_bot_user")
        root = await Category.objects.acreate(title="Root", is_folder=True)
        sub = await Category.objects.acreate(title="Sub", is_folder=True, parent=root)
        
        # Add subscription to root
        await bot_utils.toggle_subscription(999, root.id)
        
        # Check subcategory
        is_sub, sub_type = await bot_utils.is_user_subscribed(999, sub.id)
        assert is_sub is True
        assert sub_type == "inherited"
        
        # Check root
        is_sub, sub_type = await bot_utils.is_user_subscribed(999, root.id)
        assert is_sub is True
        assert sub_type == "direct"

@pytest.mark.django_db(transaction=True)
class TestAnalyticsUnitLogic:
    
    @pytest.mark.asyncio
    async def test_log_search_query_call(self):
        """Test that search query logging calls the underlying model create"""
        from apps.analytics.models import SearchQueryLog
        from apps.analytics import utils as analytics_utils
        
        # Create user
        bot_user = await BotUser.objects.acreate(telegram_id=888, username="searcher")
        
        # Call the utility
        await analytics_utils.log_search_query(user_id=888, query_text="test query", results_count=5)
        
        # Verify DB record
        def check_exists():
            return SearchQueryLog.objects.filter(user=bot_user, query_text="test query").exists()
        
        exists = await sync_to_async(check_exists)()
        assert exists is True
