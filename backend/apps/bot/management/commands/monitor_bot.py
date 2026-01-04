import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async
from apps.bot.models import BotStatus
from apps.bot.notifications import notify_admins_bot_down

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Monitor Telegram bot health and notify admins if it goes down"

    def handle(self, *args, **options):
        print("🔍 Watchdog monitor started. Keeping an eye on the bot...")
        asyncio.run(self.monitor_loop())

    async def monitor_loop(self):
        while True:
            print(f"[{timezone.now()}] Performing health check...")
            try:
                await self.check_bot_health()
            except Exception as e:
                print(f"[{timezone.now()}] Error in monitor loop: {e}")
                logger.error(f"Error in monitor loop: {e}")
            
            # Check every minute
            await asyncio.sleep(60)

    async def check_bot_health(self):
        # Get status in a thread-safe way for Django ORM
        status = await sync_to_async(BotStatus.get_status)()
        now = timezone.now()
        
        # Threshold: if no heartbeat for more than 2 minutes, consider it down
        threshold = timedelta(minutes=2)
        # Cooldown: don't send alerts more than once every hour
        alert_cooldown = timedelta(hours=1)
        
        if status.last_heartbeat:
            time_since_heartbeat = now - status.last_heartbeat
            
            if time_since_heartbeat > threshold:
                # Bot seems to be down
                should_alert = False
                
                if not status.last_alert_sent_at:
                    should_alert = True
                elif now - status.last_alert_sent_at > alert_cooldown:
                    should_alert = True
                
                if should_alert:
                    error_msg = status.error_message or "Бот перестал обновлять статус (heartbeat)."
                    logger.warning(f"Bot DOWN detected! Last heartbeat was {time_since_heartbeat.total_seconds()}s ago.")
                    
                    await notify_admins_bot_down(error_msg)
                    
                    # Update alert timestamp
                    status.last_alert_sent_at = now
                    # Also mark as not running in DB
                    status.is_running = False
                    await sync_to_async(status.save)()
            else:
                # Bot is alive. If we previously sent an alert, we should clear it
                if status.last_alert_sent_at:
                    # Bot has recovered!
                    print(f"[{timezone.now()}] Bot recovery detected!")
                    from apps.bot.notifications import send_telegram_notification, get_admin_notification_settings
                    
                    try:
                        settings_list = await get_admin_notification_settings()
                        recovery_msg = "🟢 <b>Бот снова в строю!</b>\nРабота системы восстановлена."
                        
                        for settings_obj in settings_list:
                            if settings_obj.notify_on_bot_down and settings_obj.telegram_id:
                                await send_telegram_notification(settings_obj.telegram_id, recovery_msg)
                    except Exception as e:
                        print(f"[{timezone.now()}] Error sending recovery alert: {e}")
                    
                    # Reset alert flag
                    status.last_alert_sent_at = None
                    status.is_running = True
                    await sync_to_async(status.save)()
                    logger.info("Bot is back online.")
