from django.db import migrations

def add_default_categories(apps, schema_editor):
    Category = apps.get_model('app', 'Category')
    
    default_categories = [
        {'name': 'Tops', 'description': 'Shirts, T-shirts, Blouses'},
        {'name': 'Bottoms', 'description': 'Pants, Jeans, Skirts'},
        {'name': 'Dresses', 'description': 'Dresses and Gowns'},
        {'name': 'Outerwear', 'description': 'Jackets, Coats, Sweaters'},
        {'name': 'Accessories', 'description': 'Bags, Hats, Scarves'},
        {'name': 'Footwear', 'description': 'Shoes, Boots, Sandals'},
        {'name': 'Formal Wear', 'description': 'Suits, Formal Dresses'},
        {'name': 'Activewear', 'description': 'Sports and Gym Clothing'},
        {'name': 'Swimwear', 'description': 'Swimsuits and Beachwear'},
        {'name': 'Ethnic Wear', 'description': 'Traditional and Cultural Clothing'}
    ]
    
    for category_data in default_categories:
        Category.objects.create(**category_data)

def remove_default_categories(apps, schema_editor):
    Category = apps.get_model('app', 'Category')
    Category.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0018_prelendingimage'),
    ]

    operations = [
        migrations.RunPython(add_default_categories, remove_default_categories),
    ] 