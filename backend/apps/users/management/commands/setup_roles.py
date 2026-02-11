from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.content.models import Category, DocumentVersion, Equipment
from apps.analytics.models import BotInteraction, SearchQueryLog, AuditLog
from apps.bot.models import BotUser, BotStatus
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup default roles and permissions'

    def handle(self, *args, **options):
        # 1. Content Manager (Content Full + Analytics View)
        content_manager_group, _ = Group.objects.get_or_create(name='Content Manager')
        
        # Permissions for Content Manager
        
        # A) Content: Add, Change, Delete, View
        content_models = [Category, DocumentVersion, Equipment]
        content_perms = []
        for model in content_models:
            ct = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=ct, codename__in=[
                f'add_{model._meta.model_name}',
                f'change_{model._meta.model_name}',
                f'delete_{model._meta.model_name}',
                f'view_{model._meta.model_name}',
            ])
            content_perms.extend(perms)
        
        # B) Analytics: View Only
        analytics_models = [BotInteraction, SearchQueryLog, AuditLog]
        for model in analytics_models:
            ct = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=ct, codename__in=[
                f'view_{model._meta.model_name}'
            ])
            content_perms.extend(perms)

        # C) Bot: View Only (Optional but helpful for context)
        bot_models = [BotUser, BotStatus]
        for model in bot_models:
            ct = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=ct, codename__in=[
                f'view_{model._meta.model_name}'
            ])
            content_perms.extend(perms)

        content_manager_group.permissions.set(content_perms)
        self.stdout.write(self.style.SUCCESS(f'Updated "Content Manager" group with {len(content_perms)} permissions'))

        # 2. Cleanup "Support Staff" group if exists
        try:
            Group.objects.get(name='Support Staff').delete()
            self.stdout.write(self.style.WARNING('Deleted obsolete "Support Staff" group'))
        except Group.DoesNotExist:
            pass
