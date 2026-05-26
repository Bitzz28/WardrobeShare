import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wardobe.settings')
django.setup()

from django.contrib.sites.models import Site

# Update the default site to match local environment
# This prevents "redirect_uri_mismatch" errors with Google Auth
try:
    site = Site.objects.get(id=1)
    site.domain = 'localhost:8000'
    site.name = 'WardrobeShare Local'
    site.save()
    print(f"Successfully updated Site ID 1 to {site.domain}")
except Site.DoesNotExist:
    print("Site ID 1 not found. Creating it.")
    Site.objects.create(id=1, domain='localhost:8000', name='WardrobeShare Local')
