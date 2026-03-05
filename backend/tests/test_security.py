import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

@pytest.mark.django_db
class TestSecurity:
    
    def setup_method(self):
        # Create groups for roles
        self.admin_group = Group.objects.create(name="Администратор")
        self.manager_group = Group.objects.create(name="Контент-менеджер")
        
        # Create users with different roles
        self.admin = User.objects.create_superuser(
            username="admin", 
            password="securepassword123", 
            email="admin@example.com"
        )
        self.manager = User.objects.create_user(
            username="manager", 
            password="managerpassword123"
        )
        self.manager.groups.add(self.manager_group)
        
        self.specialist = User.objects.create_user(
            username="specialist", 
            password="specialistpassword123",
            telegram_id=123456789
        )

    def test_password_hashing(self):
        """Verify that passwords are not stored in plain text (п. 1.4.4.4.3)"""
        user = User.objects.get(username="specialist")
        # Django stores password as PBKDF2 hash by default
        assert user.password.startswith('pbkdf2_sha256$')
        assert user.check_password("specialistpassword123")
        assert not user.check_password("wrongpassword")

    def test_role_assignment(self):
        """Verify role assignment and group membership (п. 1.4.2.1.3)"""
        assert self.admin.is_superuser
        assert self.manager.groups.filter(name="Контент-менеджер").exists()
        assert self.specialist.groups.count() == 0
        assert self.specialist.telegram_id == 123456789

    def test_unique_telegram_id(self):
        """Verify that telegram_id must be unique (п. 1.4.4.3.4)"""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="another_user", 
                telegram_id=123456789 # Same as specialist
            )
