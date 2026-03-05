from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import User

@receiver(post_save, sender=User)
def manage_staff_permissions(sender, instance, created, **kwargs):
    """
    Automatically adds/removes user from 'Персонал' group based on is_staff flag.
    Also ensures the group has necessary content management permissions.
    """
    group_name = "Персонал"
    
    if instance.is_staff and not instance.is_superuser:
        group, created_group = Group.objects.get_or_create(name=group_name)
        
        # If group was just created or we want to ensure permissions are up to date
        # Grant permissions for 'content' app and 'bot.SupportRequest'
        content_permissions = Permission.objects.filter(content_type__app_label='content')
        support_permissions = Permission.objects.filter(
            content_type__app_label='bot', 
            codename__in=['view_supportrequest', 'change_supportrequest']
        )
        
        group.permissions.add(*content_permissions)
        group.permissions.add(*support_permissions)
        
        instance.groups.add(group)
    elif not instance.is_staff:
        group = Group.objects.filter(name=group_name).first()
        if group:
            instance.groups.remove(group)
