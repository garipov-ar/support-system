
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.analytics.tasks import create_audit_log_task
from django.contrib.auth import get_user_model

User = get_user_model()

# Create a test user if not exists
user, created = User.objects.get_or_create(username='test_audit_user')

print("Attempting to run create_audit_log_task...")
# We call the function directly (synchronously) to see the error immediately, 
# bypassing Celery delay/worker issues for reproduction.
# The task function is decorated with @shared_task, but we can call the underlying function 
# if we access it, or just call it as a normal function (Celery tasks are callable).

try:
    create_audit_log_task(
        user_id=user.id,
        action_type='TEST_ACTION',
        details={'foo': 'bar'},
        ip_address='127.0.0.1',
        user_agent='TestAgent/1.0'
    )
    print("Task executed successfully.")
except Exception as e:
    print(f"Task failed as expected. Error: {e}")
