import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@system.com', 'admin123')
    print('Created admin user')
else:
    print('Admin user already exists')

# List all users
for u in User.objects.all():
    print(f'  {u.username} superuser={u.is_superuser}')
