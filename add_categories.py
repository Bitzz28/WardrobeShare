import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wardobe.settings')
django.setup()

from app.models import Category

# List of default categories
categories = [
    {
        'name': 'Men\'s Clothing',
        'description': 'All types of men\'s clothing including shirts, pants, suits, etc.'
    },
    {
        'name': 'Women\'s Clothing',
        'description': 'All types of women\'s clothing including dresses, tops, skirts, etc.'
    },
    {
        'name': 'Kids\' Clothing',
        'description': 'Clothing for children of all ages'
    },
    {
        'name': 'Accessories',
        'description': 'Fashion accessories like bags, belts, scarves, etc.'
    },
    {
        'name': 'Shoes',
        'description': 'All types of footwear for men, women, and children'
    },
    {
        'name': 'Jewelry',
        'description': 'Necklaces, rings, bracelets, and other jewelry items'
    },
    {
        'name': 'Traditional Wear',
        'description': 'Traditional and ethnic clothing from various cultures'
    },
    {
        'name': 'Sports Wear',
        'description': 'Sports and athletic clothing'
    },
    {
        'name': 'Formal Wear',
        'description': 'Formal clothing for special occasions'
    },
    {
        'name': 'Casual Wear',
        'description': 'Casual and everyday clothing'
    }
]

# Add categories to database
for category in categories:
    Category.objects.create(
        name=category['name'],
        description=category['description']
    )
    print(f"Added category: {category['name']}")

print("\nAll categories have been added successfully!") 