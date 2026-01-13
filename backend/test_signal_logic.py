
import os
import django
import sys
from asgiref.sync import async_to_sync

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.analytics.utils import create_audit_log
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

print(f"Testing with user: {user}")

try:
    print("Calling create_audit_log...")
    async_to_sync(create_audit_log)(
        user=user,
        action_type='LOGIN',
        ip_address='127.0.0.1',
        details={'test': 'signal_test'}
    )
    print("Call returned successfully.")
except Exception as e:
    print(f"Call failed: {e}")
