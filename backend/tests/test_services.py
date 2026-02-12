import pytest
from django.core.cache import cache
from apps.content import services
from apps.content.models import Category, DocumentVersion
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch

@pytest.mark.django_db
class TestContentServices:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):
        # Clear cache before each test
        cache.clear()
        
        # Mock run_async and notification functions to avoid threading/async issues in tests
        with patch("apps.content.signals.run_async"), \
             patch("apps.content.signals.broadcast_notification"), \
             patch("apps.content.signals.notify_admins_document_error"):
            # Root Categories
            self.root1 = Category.objects.create(title="Root 1", is_folder=True, visible_in_bot=True, order=1)
            self.root2 = Category.objects.create(title="Root 2", is_folder=True, visible_in_bot=True, order=2)
            self.hidden_root = Category.objects.create(title="Hidden Root", is_folder=True, visible_in_bot=False, order=3)
            
            # Child Categories
            self.child1 = Category.objects.create(title="Child 1", is_folder=True, visible_in_bot=True, parent=self.root1, order=1)
            
            # Documents
            self.doc1 = Category.objects.create(title="Doc 1", is_folder=False, visible_in_bot=True, parent=self.root1, order=2)
            self.doc_version = DocumentVersion.objects.create(
                content_node=self.doc1,
                version="1.0",
                file=SimpleUploadedFile("test.txt", b"content")
            )

    def test_get_root_categories(self):
        """Test fetching root categories"""
        roots = services.get_root_categories()
        assert len(roots) == 2
        assert roots[0].title == "Root 1"
        assert roots[1].title == "Root 2"
        # Verify hidden is not returned
        assert not any(r.title == "Hidden Root" for r in roots)
        
        # Test Caching
        # Modify DB directly (bypassing signals for this test or assume signal works)
        # Note: Signals are active in tests unless mutable.
        # Let's check if second call returns cached result (we can't easily mock cache here without more setup, 
        # but we can verify it doesn't crash).
        roots_cached = services.get_root_categories()
        assert len(roots_cached) == 2

    def test_get_category_details(self):
        """Test fetching category details"""
        details = services.get_category_details(self.root1.id)
        
        assert details["id"] == self.root1.id
        assert details["category"] == "Root 1"
        assert details["parent_id"] is None
        
        # Check subcategories
        assert len(details["subcategories"]) == 1
        assert details["subcategories"][0]["title"] == "Child 1"
        
        # Check documents
        assert len(details["documents"]) == 1
        assert details["documents"][0]["title"] == "Doc 1"
        assert "test" in details["documents"][0]["file_path"]

    def test_get_document_details(self):
        """Test fetching document details"""
        details = services.get_document_details(self.doc1.id)
        
        assert details["id"] == self.doc1.id
        assert details["title"] == "Doc 1"
        assert details["category_id"] == self.root1.id
        assert details["version"] == "1.0"

    def test_search_content(self):
        """Test searching content"""
        # Exact match title
        results = services.search_content("Doc 1")
        assert len(results) == 1
        assert results[0]["title"] == "Doc 1"
        
        # Partial match
        results = services.search_content("Doc")
        assert len(results) >= 1
        
        # No match
        results = services.search_content("NonExistent")
        assert len(results) == 0
