from django.db import migrations

def migrate_documents_to_nodes(apps, schema_editor):
    # Используем исторические модели для получения данных
    Document = apps.get_model('content', 'Document')
    
    # Вставляем записи через raw SQL, так как исторические модели не поддерживают MPTT
    with schema_editor.connection.cursor() as cursor:
        for doc in Document.objects.all():
            parent_id = doc.category.id if doc.category else None
            visible = doc.category.visible_in_bot if doc.category else True
            equipment_id = doc.equipment.id if doc.equipment else None
            
            # Вставляем с временными значениями MPTT-полей (1 вместо 0 для NOT NULL)
            cursor.execute("""
                INSERT INTO content_category 
                (title, parent_id, "order", visible_in_bot, is_folder, equipment_id, description, lft, rght, tree_id, level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 1, 1, 0)
            """, [doc.title, parent_id, 999, visible, False, equipment_id, doc.description])
    
    # Импортируем реальную модель (не историческую) для вызова rebuild()
    from apps.content.models import Category
    Category.objects.rebuild()



def reverse_migration(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('content', '0007_alter_category_options_alter_document_options_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_documents_to_nodes, reverse_migration),
    ]
