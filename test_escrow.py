import os
import django
from datetime import date, timedelta
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wardobe.settings')
django.setup()

from django.contrib.auth.models import User
from app.models import Profile, Post, Category, Order
from app.views import paysuccess, approve_return
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

def setup_test_data():
    # Create users
    lender_user, _ = User.objects.get_or_create(username='lender', email='lender@test.com')
    borrower_user, _ = User.objects.get_or_create(username='borrower', email='borrower@test.com')
    
    # Create profiles
    lender_profile, _ = Profile.objects.get_or_create(user=lender_user, defaults={'wallet': 0, 'profile_link': 'lender_link'})
    borrower_profile, _ = Profile.objects.get_or_create(user=borrower_user, defaults={'wallet': 1000, 'profile_link': 'borrower_link'})
    
    # Reset wallets
    lender_profile.wallet = 0
    lender_profile.save()
    borrower_profile.wallet = 1000
    borrower_profile.save()
    
    # Create category
    category, _ = Category.objects.get_or_create(name='Test Category')
    
    # Create product
    product, _ = Post.objects.get_or_create(
        user=lender_user,
        title='Test Dress',
        defaults={
            'description': 'Test Description',
            'price': 100,
            'category': category,
            'period': date.today() + timedelta(days=30),
            'quantity': 1,
            'security_deposit': 500,
            'location': 'Test City'
        }
    )
    
    # Create Order
    order = Order.objects.create(
        ecommerce_id=uuid.uuid4(),
        order_id=str(uuid.uuid4())[:10],
        user=borrower_user,
        product=product,
        quantity=1,
        amount=100,
        subtotal=100,
        security_deposit=500,
        total=600,
        full_name='Test Borrower',
        mobile_no='1234567890',
        rent_start=date.today(),
        rent_end=date.today() + timedelta(days=1),
        payment_status=False,
        order_status=False
    )
    
    return lender_user, borrower_user, product, order

def test_escrow_flow():
    print("Setting up test data...")
    lender, borrower, product, order = setup_test_data()
    
    print(f"Initial Lender Wallet: {lender.profile_set.first().wallet}")
    print(f"Initial Borrower Wallet: {borrower.profile_set.first().wallet}")
    
    # 1. Simulate Payment Success
    print("\nSimulating Payment Success...")
    factory = RequestFactory()
    request = factory.get('/')
    request.user = borrower
    
    paysuccess(request, 'pay_test_123', order.order_id)
    
    order.refresh_from_db()
    lender_profile = Profile.objects.get(user=lender)
    
    print(f"Order Payment Status: {order.payment_status}")
    print(f"Lender Wallet after Payment (Should be 0): {lender_profile.wallet}")
    
    if lender_profile.wallet != 0:
        print("FAIL: Lender received funds immediately!")
        return
    else:
        print("PASS: Funds held in escrow.")

    # 2. Simulate Return Approval
    print("\nSimulating Return Approval...")
    request = factory.get('/')
    request.user = lender  # Request must come from lender
    
    # Add message support
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    approve_return(request, order.id)
    
    lender_profile.refresh_from_db()
    borrower_profile = Profile.objects.get(user=borrower)
    
    print(f"Lender Wallet after Return (Should be 100): {lender_profile.wallet}")
    print(f"Borrower Wallet after Return (Should be 1500 [1000 start + 500 refund]): {borrower_profile.wallet}")
    
    if lender_profile.wallet == 100 and borrower_profile.wallet == 1500:
        print("PASS: Funds split correctly.")
    else:
        print("FAIL: Incorrect fund distribution.")

if __name__ == '__main__':
    test_escrow_flow()
