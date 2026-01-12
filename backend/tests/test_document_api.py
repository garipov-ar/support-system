
import pytest
from apps.content.models import Document, Category, Equipment, DocumentVersion
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.mark.django_db
def test_document_detail_api(client):
    # Setup
    category = Category.objects.create(title="Test Category")
    equipment = Equipment.objects.create(name="Test Equipment")
    document = Document.objects.create(
        title="Test Document", 
        description="Test Description", 
        category=category,
        equipment=equipment
    )
    
    version = DocumentVersion.objects.create(
        document=document,
        version="1.0",
        file=SimpleUploadedFile("test.txt", b"content"),
        author="Tester"
    )

    # Test
    response = client.get(f"/api/document/{document.id}/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == document.id
    assert data["title"] == "Test Document"
    assert data["version"] == "1.0"
    assert data["equipment_name"] == "Test Equipment"
    assert "file_path" in data

@pytest.mark.django_db
def test_document_detail_api_no_equipment(client):
    # Setup
    category = Category.objects.create(title="Test Category 2")
    document = Document.objects.create(
        title="Test Document 2", 
        description="Test Description 2", 
        category=category,
        # No equipment
    )
    
    version = DocumentVersion.objects.create(
        document=document,
        version="2.0",
        file=SimpleUploadedFile("test2.txt", b"content"),
        author="Tester"
    )

    # Test
    response = client.get(f"/api/document/{document.id}/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["version"] == "2.0"
    assert data["equipment_name"] is None
