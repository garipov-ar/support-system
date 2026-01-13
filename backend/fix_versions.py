import os
import django

# Setup Django environment manually if run directly, but we will run via shell
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# django.setup()

from django.db import connection
from apps.content.models import Category

def run():
    print("Applying Manual Fix for Orphans...")
    MAPPING = {
        1: 17, # mes3300... -> ПО для MES23xx...
        2: 16, # Mikrotik_IPTV -> Mikrotik - Настройка IPTV
        3: 18  # KeeneticGiga -> ПО для Keenetic Giga
    }
    
    with connection.cursor() as cursor:
        for ver_id, node_id in MAPPING.items():
            print(f"Linking Version {ver_id} -> Category Node {node_id}")
            cursor.execute("UPDATE content_documentversion SET content_node_id = %s WHERE id = %s", [node_id, ver_id])
            
    print("✅ Fix applied.")

if __name__ == '__main__':
    run()
