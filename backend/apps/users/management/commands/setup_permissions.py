from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.content.models import Category, Equipment, DocumentVersion

class Command(BaseCommand):
    help = "Creates default groups and permissions"

    def handle(self, *args, **options):
        # Create 'Content Managers' group
        group, created = Group.objects.get_or_create(name="Контент-менеджеры")
        
        if created:
            self.stdout.write(self.style.SUCCESS("Group 'Контент-менеджеры' created"))
        else:
            self.stdout.write("Group 'Контент-менеджеры' already exists")

        # Define models to grant access to
        models_to_grant = [Category, Equipment, DocumentVersion]
        
        permissions_to_add = []
        for model in models_to_grant:
            ct = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=ct)
            for p in perms:
                permissions_to_add.append(p)
                
        group.permissions.set(permissions_to_add)
        group.save()
        
        self.stdout.write(self.style.SUCCESS(f"Assigned {len(permissions_to_add)} permissions to 'Контент-менеджеры'"))

        # Create 'Administrators' group
        admin_group, created = Group.objects.get_or_create(name="Администраторы")
        
        if created:
            self.stdout.write(self.style.SUCCESS("Group 'Администраторы' created"))
        else:
            self.stdout.write("Group 'Администраторы' already exists")

        # Admin gets everything from Content Managers + User management
        from django.contrib.auth.models import User
        from apps.bot.models import BotUser
        
        admin_models = models_to_grant + [User, Group, BotUser]
        
        admin_perms = []
        for model in admin_models:
            ct = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=ct)
            for p in perms:
                admin_perms.append(p)

        admin_group.permissions.set(admin_perms)
        admin_group.save()
        
        self.stdout.write(self.style.SUCCESS(f"Assigned {len(admin_perms)} permissions to 'Администраторы'"))
