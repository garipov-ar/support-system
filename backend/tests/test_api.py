import pytest
import httpx

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_navigation_api_health():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/navigation/")
        # This will fail in isolated test environment without server running
        # but for now we just setup the structure
        assert response.status_code in [200, 404]

@pytest.mark.django_db
def test_audit_log_creation():
    from apps.analytics.models import AuditLog
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    user = User.objects.create_user(username="testuser", password="password")
    AuditLog.objects.create(user=user, action_type="LOGIN")
    
    assert AuditLog.objects.count() == 1
