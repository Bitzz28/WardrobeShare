import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wardobe.settings')
django.setup()

from django.core.mail import send_mail

try:
    send_mail(
        'Test Email from Wardrobe Share',
        'This is a test email to verify the email configuration is working correctly.',
        'wardrobesharez@gmail.com',
        ['21eg110b41@gmail.com'],
        fail_silently=False,
    )
    print("Test email sent successfully!")
except Exception as e:
    print(f"Error sending email: {e}")