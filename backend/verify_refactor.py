import os
import django
import sys
import asyncio

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.content import services
from asgiref.sync import sync_to_async

def test_services_sync():
    print("Testing Sync Services...")
    categories = services.get_root_categories()
    print(f"Root Categories: {list(categories)}")
    
    if categories:
        cat_id = categories[0].id
        details = services.get_category_details(cat_id)
        print(f"Category Details for {cat_id} successfully fetched.")
        
        # Check structure
        assert "subcategories" in details
        assert "documents" in details
        assert "path" in details
    
    results = services.search_content("a") # Search for something common
    print(f"Search Results (query='a'): {len(results)} items found.")

async def test_services_async():
    print("\nTesting Async Wrappers (Simulating Bot)...")
    # Simulate build_root_keyboard
    categories = await sync_to_async(lambda: list(services.get_root_categories()))()
    print(f"Async Root Categories: {len(categories)}")
    
    if categories:
        cat_id = categories[0].id
        # Simulate category_handler
        details = await sync_to_async(services.get_category_details)(cat_id)
        print(f"Async Category Details for {cat_id} successfully fetched.")

if __name__ == "__main__":
    try:
        test_services_sync()
        asyncio.run(test_services_async())
        print("\nVerification Successful!")
    except Exception as e:
        print(f"\nVerification Failed: {e}")
        import traceback
        traceback.print_exc()
