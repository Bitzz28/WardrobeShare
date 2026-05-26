from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory,CheckboxInput,FileInput
from django.contrib import messages
from django.core.files import File
from django.db.models import Q, F, ExpressionWrapper, FloatField, Sum, Avg
from io import BytesIO
from django.core.mail import send_mail
from datetime import datetime,timedelta,date
import razorpay
import qrcode
import uuid
from .models import (
    Post, PostImage, Profile, Order, Review, 
    Category, Slider, ProductView,
    ChatRoom, ChatMessage, ChatAttachment,
    DigitalContract, IDVerification, Notification,
    VerificationRequest, PreLendingImage
)
from .forms import *
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError
from math import radians, sin, cos, sqrt, asin
import json
from django.views import View
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
from django.utils import timezone
from django.views.decorators.http import require_POST

# Create your views here.
@login_required
def home(r):
    slides = Slider.objects.order_by('-id')
    categories = Category.objects.all()
    
    if not Profile.objects.filter(user=r.user).exists():
        messages.error(r, 'Please fill your profile first')
        return redirect('/accounts/profile')
    
    # Get user's profile and location
    user_profile = Profile.objects.get(user=r.user)
    user_city = user_profile.city
    
    # Get all available items excluding user's own items
    products = Post.objects.filter(availability=True).exclude(user=r.user)
    
    # Get nearby items (items in the same city)
    nearby_products = products.filter(location__icontains=user_city)
    
    # Check if user wants to see only nearby items
    show_nearby = r.GET.get('nearby', 'false') == 'true'
    
    # Filter products based on user's preference
    if show_nearby:
        products = nearby_products
    
    context = {
        "slides": slides,
        "products": products,
        "categories": categories,
        "show_nearby": show_nearby,
        "user_city": user_city,
        "nearby_count": nearby_products.count(),
        "total_count": products.count()
    }
    
    return render(r, 'index.html', context)
@login_required
def search(request):
    # Get all available items by default
    posts = Post.objects.filter(availability=True)
    
    if request.method == 'POST':
        query = request.POST.get('query', '')
        category = request.POST.get('category', '')
        gender = request.POST.get('gender', '')
        price = request.POST.get('price', '')
        location = request.POST.get('location', '')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        distance = request.POST.get('distance', 10)  # Default 10km radius

        if query:
            posts = posts.filter(Q(title__icontains=query) | Q(description__icontains=query))
        
        if category:
            posts = posts.filter(category_id=category)
        
        if gender:
            posts = posts.filter(gender=gender)
        
        if price:
            posts = posts.filter(price__lte=float(price))
        
        if location and latitude and longitude:
            try:
                lat = float(latitude)
                lon = float(longitude)
                distance_km = float(distance)
                
                # Simple bounding box calculation (approximate)
                # 1 degree is approximately 111km at the equator
                lat_diff = distance_km / 111.0
                lon_diff = distance_km / (111.0 * cos(radians(lat)))
                
                posts = posts.filter(
                    latitude__gte=lat - lat_diff,
                    latitude__lte=lat + lat_diff,
                    longitude__gte=lon - lon_diff,
                    longitude__lte=lon + lon_diff
                )
                
                # Calculate actual distances and filter
                posts = posts.annotate(
                    distance=ExpressionWrapper(
                        sqrt(
                            pow(F('latitude') - lat, 2) +
                            pow(F('longitude') - lon, 2)
                        ) * 111.0,  # Convert to kilometers
                        output_field=FloatField()
                    )
                ).filter(distance__lte=distance_km).order_by('distance')
                
            except (ValueError, TypeError):
                messages.error(request, 'Invalid location coordinates provided')

    context = {
        'posts': posts,
        'query': request.POST.get('query', ''),
        'category': request.POST.get('category', ''),
        'gender': request.POST.get('gender', ''),
        'price': request.POST.get('price', ''),
        'location': request.POST.get('location', ''),
        'distance': request.POST.get('distance', 10),
        'categories': Category.objects.all(),
        'gender_choices': [('Male', 'Male'), ('Female', 'Female'), ('Unisex', 'Unisex')],
    }
    
    return render(request, 'search.html', context)
@login_required()
def profile(r):
    form =ProfileForm()
    profile=""
    if Profile.objects.filter(user=r.user).exists():
        profile=Profile.objects.get(user=r.user)
        form = ProfileForm(instance=profile)
    if r.method=='POST':
        form = ProfileForm(r.POST,instance=profile or None,files=r.FILES)
        if form.is_valid():
            k=form.save(commit=False)
            k.user=r.user
            k.save()
            messages.success(r,'Profile Updated Successfully')
            return redirect('/accounts/profile')
    return render(r,'account/profile.html',{"form":form,"profile":profile})
@login_required()
def new_post(request):
    if not Profile.objects.filter(user=request.user).exists():
        messages.error(request,'Please fill your profile first')
        return redirect('/accounts/profile')
    product_form = PostForm(request.POST or None,request.FILES or None)
    images_formset = inlineformset_factory(Post, PostImage, fields=('image',), extra=3,can_delete=True)(request.POST or None,request.FILES or None, instance=Post()) 
    for form in images_formset:
        for field in form.fields.values():
            if isinstance(field.widget, FileInput):
                field.widget.attrs.update({'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400'})
            if isinstance(field.widget, CheckboxInput):
                field.widget.attrs.update({'class': 'w-4 h-4 border border-gray-300 rounded bg-gray-50 focus:ring-3 focus:ring-blue-300 dark:bg-gray-700 dark:border-gray-600 dark:focus:ring-blue-600 dark:ring-offset-gray-800 dark:focus:ring-offset-gray-800'})
    if request.method == 'POST':
        if product_form.is_valid() and images_formset.is_valid():
            p = product_form.save(commit=False)
            p.user = request.user
            p.profile = Profile.objects.get(user=request.user)
            p.delivery_type = 'Self Pickup'  # Enforce only self pickup
            p.save()
            images_formset.instance = p
            images_formset.save()
            messages.success(request,'Post Created Successfully')
            return redirect(f'/post/edit/{p.id}')
        print(product_form.errors)
    return render(request, 'new_post.html', {'form': product_form, 'formset': images_formset})
@login_required
def editpost(request, id):
    if not Profile.objects.filter(user=request.user).exists():
        messages.error(request,'Please fill your profile first')
        return redirect('/accounts/profile')
    p=Post.objects.get(id=id)
    if not p.user==request.user:
        messages.error(request,'You are not the owner of this post')
        return redirect('/post/all')
    product_form = PostForm(request.POST or None,request.FILES or None,instance=p)
    images_formset = inlineformset_factory(Post, PostImage, fields=('image',), extra=3,can_delete=True)(data=request.POST or None,files=request.FILES or None, instance=p) 
    for form in images_formset:
        for field in form.fields.values():
            if isinstance(field.widget, FileInput):
                field.widget.attrs.update({'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400'})
            if isinstance(field.widget, CheckboxInput):
                field.widget.attrs.update({'class': 'w-4 h-4 border border-gray-300 rounded bg-gray-50 focus:ring-3 focus:ring-blue-300 dark:bg-gray-700 dark:border-gray-600 dark:focus:ring-blue-600 dark:ring-offset-gray-800 dark:focus:ring-offset-gray-800'})
    if request.method == 'POST':
        if product_form.is_valid() and images_formset.is_valid():
            product_form.save()
            images_formset.save()
            messages.success(request,'Post Updated Successfully')
            return redirect(f'/post/edit/{id}')
    return render(request, 'new_post.html', {'form': product_form, 'formset': images_formset,"pid":id})
@login_required
def deletepost(request,id):
    if not Profile.objects.filter(user=request.user).exists():
        messages.error(request,'Please fill your profile first')
        return redirect('/accounts/profile')
    p=Post.objects.get(id=id)
    if p.user==request.user:
        p.delete()
        messages.success(request,'Post Deleted Successfully')
        return redirect('/post/all')
    messages.error(request,'You are not the owner of this post')
    return redirect('/post/all')
@login_required
def user_posts(request):
    if not Profile.objects.filter(user=request.user).exists():
        messages.error(request,'Please fill your profile first')
        return redirect('/accounts/profile')
    posts = Post.objects.filter(user=request.user).order_by("-id")
    return render(request, 'user_posts.html', {'data': posts})
@login_required
def post_reviews(request):
    if not Profile.objects.filter(user=request.user).exists():
        messages.error(request,'Please fill your profile first')
        return redirect('/accounts/profile')
    comments=Comment.objects.filter(post__user=request.user).order_by("-id")
    return render(request, 'user_post_reviews.html', {"data":comments})
@login_required
def profile_reviews(request):
    if not Profile.objects.filter(user=request.user).exists():
        messages.error(request,'Please fill your profile first')
        return redirect('/accounts/profile')
    comments=Review.objects.filter(profile__user=request.user).order_by("-id")
    return render(request, 'user_profile_reviews.html', {"data":comments})
@login_required
def view_post(request,id):
    form=CommentForm()
    posts = Post.objects.get(id=id)
    buy=posts.availability and date.today()<=posts.period and posts.user!=request.user and posts.quantity>0
    m=10 if posts.quantity>10 else posts.quantity
    avail=posts.availability and date.today()<=posts.period
    similar_posts = Post.objects.filter(category=posts.category).exclude(user=request.user).exclude(id=id)
    
    if request.method == 'POST':
        if request.user==posts.user:
            messages.error(request,'You cannot comment on your own post')
            return redirect(f'/post/view/{id}')
        form = CommentForm(request.POST,request.FILES)
        if form.is_valid():
            pp=form.save(commit=False)
            pp.post=posts
            pp.user=Profile.objects.get(user=request.user)
            pp.empty="*"*(5-len(form.cleaned_data["rating"]))
            pp.save()
    comments=Comment.objects.filter(post=id)
    return render(request, 'post.html', {
        'data': posts,
        "buy":buy,
        "max":m,
        "available":avail,
        "similar":similar_posts,
        "form":form,
        "comments":comments
    })


@login_required
def makeorder(request, id, q):
    product = Post.objects.get(id=id)
    form = MakeOrderForm()
    
    # Check quantity and availability
    if q > product.quantity or q > 10 or q < 1:
        messages.error(request, 'Quantity is more than available')
        return redirect(f'/post/view/{product.id}')
    if not product.availability or date.today() > product.period:
        messages.error(request, 'Product is not available')
        return redirect(f'/post/view/{product.id}')
    if product.user == request.user:
        messages.error(request, 'You can not rent your own product')
        return redirect(f'/post/view/{product.id}')
    
    if request.method == 'POST':
        form = MakeOrderForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data['rent_start']
            end = form.cleaned_data['rent_end']
            
            if end > product.period:
                form.add_error('rent_end', "Not Available till this date")
            
            if form.errors:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please correct the errors below.',
                    'errors': form.errors
                }, status=400)
            
            # Calculate rental amount
            days = (end - start).days
            amount = round(product.price * days)  # Daily rate
            security_deposit = product.security_deposit if product.security_deposit else 0
            
            # Calculate total including security deposit
            subtotal = q * amount
            total = subtotal + security_deposit
            
            # Create rental request order
            ecom = uuid.uuid4()
            new_order = Order(
                ecommerce_id=ecom,
                order_id=str(uuid.uuid4())[:10],
                rental_status='pending_approval',  # Initial status
                delivery_status="Pending",
                user=request.user,
                product=product,
                quantity=q,
                amount=amount,
                subtotal=subtotal,
                security_deposit=security_deposit,
                total=total,
                full_name=form.cleaned_data['full_name'],
                mobile_no=form.cleaned_data['mobile_no'],
                alternate_no=form.cleaned_data.get('alternate_no'),
                order_date=datetime.today(),
                delivery_date=datetime.today() + timedelta(days=7),
                rent_start=start,
                rent_end=end
            )
            new_order.save()

            # Send email notification to lender
            lender_subject = "New Rental Request - WardrobeShare"
            lender_message = f"""
Dear {product.user.username},

You have received a new rental request for your item:

Item Details:
- Title: {product.title}
- Rental Period: {start.strftime('%d-%m-%Y')} to {end.strftime('%d-%m-%Y')}
- Quantity: {q}
- Total Amount: ₹{total}

Borrower Details:
- Name: {form.cleaned_data['full_name']}
- Contact: {form.cleaned_data['mobile_no']}
- Delivery Type: Self Pickup

Please log in to your account to approve or decline this request:
{settings.SITE_URL}/lender/orders/

Best regards,
WardrobeShare Team
            """
            
            send_mail(
                lender_subject,
                lender_message,
                "wardrobesharez@gmail.com",
                [product.user.email],
                fail_silently=True,
            )

            # Create notification for lender
            create_notification(
                user=product.user,
                notification_type='new_rental_request',
                title='New Rental Request',
                message=f'You have received a new rental request for {product.title}',
                link='/lender/orders/'
            )
            
            # Return success response with redirect to home
            return JsonResponse({
                'status': 'success',
                'message': 'Your rental request has been sent successfully! The lender will review your request.',
                'redirect_url': '/'  # Redirect to home page
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Please correct the errors below.',
                'errors': form.errors
            }, status=400)
    
    return render(request, 'makeorder.html', {"form": form, "post": product})

@login_required
def orderpayment(r,id):
    ord=Order.objects.get(id=id)
    return render(r,'payment.html',{"order":ord})
@login_required
@login_required
def paysuccess(r,pay,id):
    for i in Order.objects.filter(order_id=id):
        if Post.objects.filter(id=i.product_id):
            pp=Post.objects.get(id=i.product_id)
            pp.quantity=pp.quantity-i.quantity
            pp.save()
            # Funds are held in escrow, not transferred to wallet immediately
            # pp=pp.profile
            # pp.wallet=pp.wallet+float(i.total)
            # pp.save()
        update_order(i.ecommerce_id,pay,True)
    return redirect('/orders')
@login_required
def payfailed(r,pay,id):
    for i in Order.objects.filter(order_id=id):
        update_order(i.ecommerce_id,pay,False)
    return redirect('/orders')

def update_order(id, pay, status):
    try:
        ob = Order.objects.get(ecommerce_id=id)
        ob.payment_id = pay
        ob.order_status = True
        ob.payment_status = status

        # Set delivery status for failed payment
        if not status:
            ob.delivery_status = "Payment Failed"

        # Common email details
        order_summary = f"""
Order ID: {ob.order_id}
Order Date: {ob.order_date.strftime('%d-%b-%Y') if ob.order_date else 'N/A'}
        """+f"Estimated Delivery Date: {ob.delivery_date.strftime('%d-%b-%Y') if ob.delivery_date else 'N/A'}" if ob.product.delivery_type=="Courier" else ""
        # Return Before: {(ob.delivery_date + timedelta(days=7)).strftime('%d-%b-%Y') if ob.delivery_date else 'N/A'}

        product_summary = f"""
Product Name: {ob.product.title}
Product ID: {ob.product.id}
Price per Unit: ₹{ob.product.price}
Amount per Unit: ₹{ob.amount}
Quantity: {ob.quantity}
Subtotal: ₹{ob.subtotal}
        """

        delivery_summary = f"""
Delivery Type: {ob.product.delivery_type}
Recipient Name: {ob.full_name}
Mobile Numbers: {ob.mobile_no}, {ob.alternate_no}
        """

        payment_summary = f"""
Payment ID: {ob.payment_id if ob.payment_id else 'N/A'}
Payment Status: {"Paid" if ob.payment_status else "Not Paid"}
Total Amount: ₹{ob.total}
        """

        # Subject lines based on delivery status
        delivery_status = ob.delivery_status
        buyer_subject = f"Order {delivery_status} - Wardrobe Share"
        seller_subject = f"New Order Notification - Order {delivery_status}"

        # Buyer email body
        buyer_body = f"""
Dear {ob.user.username},

Your order with Wardrobe Share is currently {delivery_status}. Below are your order details:

Order Summary:
{order_summary}

Product Details:
{product_summary}

User Details:
{delivery_summary}

Payment Summary:
{payment_summary}

Thank you for shopping with Wardrobe Share. If you have any questions, feel free to contact us at support@wardrobeshare.com.

Warm regards,
Wardrobe Share Team
        """

        # Seller email body
        seller_body = f"""
Dear {ob.product.user.username},

A new order has been placed for your product. Below are the details:

Order Summary:
{order_summary}

Buyer Information:
Buyer Name: {ob.user.username}
Buyer Email: {ob.user.email}
{delivery_summary}

Product Details:
{product_summary}

Payment Summary:
{payment_summary}

Please prepare the product for delivery promptly. If you have any questions, feel free to contact us at support@wardrobeshare.com.

Best regards,
Wardrobe Share Team
        """

        # Adjust for payment failure
        if not status:
            buyer_subject = "Order Payment Failed - Wardrobe Share"
            buyer_body = f"""
Dear {ob.user.username},

Unfortunately, the payment for your order could not be processed. Below are the details of your order:

Order Summary:
{order_summary}

Please try placing the order again or contact us at support@wardrobeshare.com for assistance.

Warm regards,
Wardrobe Share Team
            """
            seller_body = None  # No email to seller for failed payment

        # Generate QR code only if payment is successful
        if status:
            try:
                qr_data = f"""
Order Details:
{order_summary}

Product Details:
{product_summary}

Delivery Details:
{delivery_summary}

Payment Summary:
{payment_summary}
                """
                qr = qrcode.make(qr_data)
                stream = BytesIO()
                qr.save(stream, 'PNG')
                filename = f'qrcode_{ob.order_id}.png'
                ob.qrcode.save(filename, File(stream), save=False)
            except Exception as e:
                print(f"Error generating QR code: {e}")

        # Send emails
        send_mail(buyer_subject, buyer_body, "wardrobesharez@gmail.com", [ob.user.email])
        if seller_body:
            send_mail(seller_subject, seller_body, "wardrobesharez@gmail.com", [ob.product.user.email])

        ob.save()

    except Order.DoesNotExist:
        print(f"Order with ecommerce_id {id} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

#orders
@login_required
def orders(r):
    ord = Order.objects.filter(user=r.user, order_status=True).order_by("-id")  # Corrected filter chain

    # Loop through the orders queryset
    for order in ord:  # Use `ord` here instead of `orders`
        if order.rent_end and order.rent_start:
            order.rent_duration = order.rent_end - order.rent_start
        else:
            order.rent_duration = timedelta(days=0)

    return render(r, 'orders.html', {"orders": ord})

@login_required
def orderdetails(r, id=None, ecommerce_id=None):
    if id:
        i = Order.objects.get(id=id)
    else:
        i = Order.objects.get(ecommerce_id=ecommerce_id)
    returndate=i.delivery_date+timedelta(days=7)
    pending=0
    confirmed=0
    cancelled=0
    shipping=0
    shipped=0
    outfordelivery=0
    delivered=0
    returned=0
    refunded=0
    refundcancel=0
    cancel=0
    refund=0
    if i.delivery_status=="Pending":
        pending=1
    elif i.delivery_status=="Confirmed":
        confirmed=1
    elif i.delivery_status=="Cancelled":
        cancelled=1
    elif i.delivery_status=="Shipping":
        shipping=1
    elif i.delivery_status=="Shipped":
        shipped=1
    elif i.delivery_status=="Out for Delivery":
        outfordelivery=1
    elif i.delivery_status=="Delivered":
        delivered=1
    elif i.delivery_status=="Returned":
        returned=1
    elif i.delivery_status=="Refunded":
        refunded=1
    elif i.delivery_status=="Refund Cancel":
        refundcancel=1
    if pending or confirmed or shipped or shipping or outfordelivery:
        cancel=1
    if delivered and datetime.now().date()<=returndate:
        refund=1
    context={
        "i":i,
        "pending":pending,
        "returndate":returndate,
        "confirmed":confirmed,
        "cancelled":cancelled,
        "shipping":shipping,
        "shipped":shipped,
        "outfordelivery":outfordelivery,
        "returned":returned,
        "refunded":refunded,
        "refundcancel":refundcancel,
        "delivered":delivered,
        "cancel":cancel,
        "refund":refund
    }
    

    return render(r,'orderdetails.html',context)
@login_required
def cancelorder(r,id):
    o=Order.objects.get(id=id)
    o.delivery_status="Cancelled"
    o.save()

    # If the order was declined by the lender and now cancelled by the borrower
    if o.rental_status == 'declined':
        # Create notification for the lender
        create_notification(
            user=o.product.user,
            notification_type='order_status',
            title='Order Cancelled',
            message=f'The borrower has cancelled their order for {o.product.title} after it was declined.',
            link=f'/order/{o.ecommerce_id}'
        )
        
        # Delete the previous notification about accepting/declining the order
        Notification.objects.filter(
            user=o.product.user,
            notification_type='new_rental_request',
            message__contains=o.product.title
        ).delete()

    return redirect(f'/order/{o.ecommerce_id}')
@login_required
def approve_return(r, id):
    """
    Lender approves the return of the item.
    This triggers the release of funds from Escrow:
    - Lender receives Rental Fee (amount * quantity)
    - Borrower receives Security Deposit (security_deposit)
    """
    o = get_object_or_404(Order, id=id)
    
    # Ensure only the lender can approve the return
    if r.user != o.product.user:
        messages.error(r, 'Only the lender can approve the return.')
        return redirect(f'/order/{o.ecommerce_id}')
        
    if o.funds_released:
        messages.warning(r, 'Funds have already been released for this order.')
        return redirect(f'/order/{o.ecommerce_id}')

    # Update order status
    o.delivery_status = "Returned"
    o.funds_released = True
    o.save()

    # 1. Credit Lender Wallet (Rental Fee)
    lender_profile = Profile.objects.get(user=o.product.user)
    rental_fee = o.subtotal  # This is price * quantity
    lender_profile.wallet += rental_fee
    lender_profile.save()

    # 2. Credit Borrower Wallet (Security Deposit)
    borrower_profile = Profile.objects.get(user=o.user)
    security_deposit = o.security_deposit
    borrower_profile.wallet += security_deposit
    borrower_profile.save()
    
    # Create notification for Borrower
    create_notification(
        user=o.user,
        notification_type='order_status',
        title='Return Approved & Funds Released',
        message=f'Your return for {o.product.title} has been approved. Security deposit of ₹{security_deposit} has been refunded to your wallet.',
        link=f'/order/{o.ecommerce_id}'
    )

    # Create notification for Lender
    create_notification(
        user=o.product.user,
        notification_type='order_status',
        title='Funds Received',
        message=f'Rental fee of ₹{rental_fee} for {o.product.title} has been credited to your wallet.',
        link=f'/order/{o.ecommerce_id}'
    )

    messages.success(r, f'Return approved. ₹{rental_fee} credited to your wallet. ₹{security_deposit} refunded to borrower.')
    return redirect(f'/order/{o.ecommerce_id}')
@login_required
def user_orders(r):
    if not Profile.objects.filter(user=r.user).exists():
        messages.error(r,'Please fill your profile first')
        return redirect('/accounts/profile')
    order=Order.objects.filter(order_status=True,product__user=r.user).order_by("-id")
    return render(r,'user_orders.html',{"data":order})
@login_required
def post_profile(request,id):
    profile=Profile.objects.get(id=id)
    order=Post.objects.filter(user=profile.user)
    reviews=Review.objects.filter(profile=profile)
    form=ReviewForm()
    if request.method == 'POST':
        if request.user==profile.user:
            messages.error(request,'You cannot comment on your own profile')
            return redirect(f'/post/profile/{id}')
        form = ReviewForm(request.POST,request.FILES)
        if form.is_valid():
            pp=form.save(commit=False)
            pp.profile=profile
            pp.user=Profile.objects.get(user=request.user)
            pp.empty="*"*(5-len(form.cleaned_data["rating"]))
            pp.save()
    return render(request,'profile_reviews.html',{"data":order,"reviews":reviews,"profile":profile,"form":form})
@login_required
def user_orders_confirm(r,id):
    order=Order.objects.get(id=id)
    if  order.product.user==r.user:
        order.delivery_status="Confirmed"
        order.save()
        update_order(order.ecommerce_id,order.payment_id,order.payment_status)
        messages.success(r,'Order has been confirmed')
        return redirect('/post/orders')
    return redirect('/post/orders')
@login_required
def user_orders_cancel(r,id):
    order=Order.objects.get(id=id)
    if  order.delivery_status=="Pending" and order.product.user==r.user:
        order.delivery_status="Cancelled"
        order.save()
        update_order(order.ecommerce_id,order.payment_id,order.payment_status)
        messages.success(r,'Order has been cancelled')
        return redirect('/post/orders')
    return redirect('/post/orders')

@login_required
def user_orders_update(r,id):
    form=OrderForm()
    order=Order.objects.get(id=id)
    form=OrderForm(instance=order)
    if r.method=="POST":
        form=OrderForm(r.POST,instance=order)
        if form.is_valid():
            form.save()
            update_order(order.ecommerce_id,order.payment_id,order.payment_status)
            return redirect(f'/post/orders')
    return render(r,"user_orders_update.html",{"form":form})

def view_profile_by_link(request, profile_link):
    try:
        profile = Profile.objects.get(profile_link=profile_link)
        posts = Post.objects.filter(user=profile.user)
        return render(request, 'profile_view.html', {
            'profile': profile,
            'posts': posts
        })
    except Profile.DoesNotExist:
        messages.error(request, 'Profile not found')
        return redirect('home')

@login_required
def toggle_wishlist(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, post=post)
    if not created:
        wishlist_item.delete()
        messages.success(request, 'Removed from wishlist')
    else:
        messages.success(request, 'Added to wishlist')
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def view_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def post_add(request):
    if not Profile.objects.filter(user=request.user).exists():
        messages.error(request, 'Please fill your profile first')
        return redirect('/accounts/profile')
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.profile = request.user.profile
            
            # Save latitude and longitude if provided
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            if latitude and longitude:
                try:
                    post.latitude = float(latitude)
                    post.longitude = float(longitude)
                except (ValueError, TypeError):
                    messages.warning(request, 'Invalid location coordinates provided')
            
            post.save()
            messages.success(request, 'Item listed successfully')
            return redirect('/user/posts')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = PostForm()
    
    return render(request, 'post_add.html', {'form': form})

@login_required
def lender_orders(request):
    """View for lenders to see and manage rental requests"""
    if not Profile.objects.filter(user=request.user).exists():
        messages.error(request, 'Please fill your profile first')
        return redirect('/accounts/profile')
    
    # Get all orders for items owned by the lender
    pending_orders = Order.objects.filter(
        product__user=request.user,
        rental_status='pending_approval'
    ).order_by('-order_date')
    
    approved_orders = Order.objects.filter(
        product__user=request.user,
        rental_status='approved'
    ).order_by('-order_date')
    
    declined_orders = Order.objects.filter(
        product__user=request.user,
        rental_status='declined'
    ).order_by('-order_date')
    
    return render(request, 'lender/orders.html', {
        'pending_orders': pending_orders,
        'approved_orders': approved_orders,
        'declined_orders': declined_orders
    })

@login_required
def handle_rental_request(request, order_id, action):
    """Handle approval/decline of rental requests"""
    try:
        order = Order.objects.get(id=order_id, product__user=request.user)
        
        if action not in ['approve', 'decline']:
            messages.error(request, 'Invalid action')
            return redirect('lender_orders')
        
        if order.rental_status != 'pending_approval':
            messages.error(request, 'This request has already been processed')
            return redirect('lender_orders')
        
        # Update order status
        order.rental_status = 'approved' if action == 'approve' else 'declined'
        order.save()
        
        if action == 'approve':
            # Create chat room for approved rental
            chat_room = ChatRoom.objects.create(order=order)
            
            # Create rental approval notification for borrower (links to order details)
            create_notification(
                user=order.user,
                notification_type='rental_approved',
                title='Rental Request Approved!',
                message=f'Your rental request for {order.product.title} has been approved.',
                link=f'/order/{order.ecommerce_id}'  # Link to order details
            )
            
            # Create separate chat enabled notification for borrower (links to chat)
            create_notification(
                user=order.user,
                notification_type='chat_enabled',
                title='Chat Available',
                message=f'You can now chat with {order.product.user.username} (Lender) about {order.product.title}',
                link=f'/chat/{chat_room.id}'  # Link to chat room
            )
            
            # Create chat enabled notification for lender
            create_notification(
                user=order.product.user,
                notification_type='chat_enabled',
                title='Chat Available',
                message=f'You can now chat with {order.user.username} (Borrower) about {order.product.title}',
                link=f'/chat/{chat_room.id}'  # Link to chat room
            )
        else:
            create_notification(
                user=order.user,
                notification_type='rental_declined',
                title='Rental Request Declined',
                message=f'Your rental request for {order.product.title} has been declined by the lender.',
                link=f'/order/{order.ecommerce_id}'
            )
        
        # Send email notification to borrower
        subject = f"Rental Request {order.rental_status.title()} - WardrobeShare"
        message = f"""
Dear {order.user.username},

Your rental request for {order.product.title} has been {order.rental_status}!

{'You can now chat with the lender to discuss the rental details.' if action == 'approve' else 'The lender has declined your rental request.'}

Order Details:
- Item: {order.product.title}
- Rental Period: {order.rent_start.strftime('%d-%m-%Y')} to {order.rent_end.strftime('%d-%m-%Y')}
- Total Amount: ₹{order.total}

{'Visit your order page to view details: ' + settings.SITE_URL + '/order/' + str(order.ecommerce_id) if action == 'approve' else ''}
{'Chat with the lender: ' + settings.SITE_URL + '/chat/' + str(chat_room.id) if action == 'approve' else ''}

Best regards,
WardrobeShare Team
        """
        
        send_mail(
            subject,
            message,
            "wardrobesharez@gmail.com",
            [order.user.email],
            fail_silently=True,
        )
        
        messages.success(request, f'Rental request {order.rental_status} successfully')
        return redirect('lender_orders')
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('lender_orders')

@login_required
def notifications(request):
    """View to display all notifications"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')  # Show newest first
    return render(request, 'notifications.html', {
        'notifications': notifications,
        'user': request.user
    })

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False}, status=404)

@login_required
def get_unread_notifications_count(request):
    """Get count of unread notifications"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

def create_notification(user, notification_type, title, message, link=''):
    """Helper function to create notifications"""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )
    return notification

@login_required
def chat_room(request, chat_id):
    chat_room = get_object_or_404(ChatRoom, id=chat_id)
    
    # Check if user is part of the chat
    if request.user not in [chat_room.order.user, chat_room.order.product.user]:
        messages.error(request, 'You do not have access to this chat room')
        return redirect('active_chats')
    
    # Get chat messages
    chat_messages = ChatMessage.objects.filter(
        chat_room=chat_room
    ).order_by('timestamp')
    
    # Get all verification requests
    govt_id_verifications = VerificationRequest.objects.filter(
        chat_room=chat_room,
        type='govt_id'
    ).order_by('-created_at').select_related('chat_room', 'chat_room__order')
    
    selfie_verifications = VerificationRequest.objects.filter(
        chat_room=chat_room,
        type='selfie'
    ).order_by('-created_at').select_related('chat_room', 'chat_room__order')
    
    # Add type to each verification object for template use
    for verification in govt_id_verifications:
        verification.type = 'govt_id'
    
    for verification in selfie_verifications:
        verification.type = 'selfie'
    
    # Get the contract for this chat room's order
    contract = DigitalContract.objects.filter(order=chat_room.order).first()
    
    context = {
        'chat_room': chat_room,
        'messages': chat_messages,
        'other_user': chat_room.order.user if request.user == chat_room.order.product.user else chat_room.order.product.user,
        'govt_id_verifications': govt_id_verifications,
        'selfie_verifications': selfie_verifications,
        'is_lender': request.user == chat_room.order.product.user,
        'is_borrower': request.user == chat_room.order.user,
        'contract': contract,
    }
    
    return render(request, 'chat/chat_room.html', context)

@login_required
def get_chat_messages(request, chat_id, last_message_id=None):
    """API endpoint to get new messages"""
    try:
        chat_room = ChatRoom.objects.get(id=chat_id)
        order = chat_room.order
        
        # Verify user is either the lender or borrower
        if request.user not in [order.user, order.product.user]:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get messages after the last_message_id, excluding system notifications
        messages = chat_room.messages.filter(
            message_type='text'  # Only get actual text messages
        )
        if last_message_id:
            messages = messages.filter(id__gt=last_message_id)
        
        # Mark messages as read
        messages.exclude(sender=request.user).update(is_read=True)
        
        return JsonResponse({
            'messages': [{
                'id': msg.id,
                'message': msg.message,
                'message_type': msg.message_type,
                'sender': {
                    'id': msg.sender.id,
                    'username': msg.sender.username
                },
                'timestamp': msg.timestamp.isoformat(),
            } for msg in messages]
        })
        
    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'Chat room not found'}, status=404)

@login_required
def get_unread_messages_count(request):
    """Get count of unread messages across all chats"""
    count = ChatMessage.objects.filter(
        chat_room__in=ChatRoom.objects.filter(
            Q(order__user=request.user) | Q(order__product__user=request.user)
        ),
        is_read=False
    ).exclude(sender=request.user).count()
    
    return JsonResponse({'count': count})

@login_required
def active_chats(request):
    """View to list all active chats for the user"""
    # Get all chat rooms where user is either lender or borrower
    chat_rooms = ChatRoom.objects.filter(
        Q(order__user=request.user) | Q(order__product__user=request.user),
        is_active=True,
        order__rental_status='approved'
    ).select_related('order', 'order__product', 'order__user', 'order__product__user')
    
    # Get unread message counts and last message for each chat
    for chat in chat_rooms:
        chat.unread_count = chat.messages.filter(
            is_read=False
        ).exclude(sender=request.user).count()
        
        # Get the last message
        last_message = chat.messages.order_by('-timestamp').first()
        chat.last_message = last_message.message if last_message else ''
        chat.last_message_time = last_message.timestamp if last_message else chat.created_at
        
        # Determine the other party in the chat
        chat.other_user = chat.order.user if request.user == chat.order.product.user else chat.order.product.user
        
    # Sort chats by last message time
    chat_rooms = sorted(chat_rooms, key=lambda x: x.last_message_time, reverse=True)
    
    return render(request, 'chat/active_chats.html', {
        'chat_rooms': chat_rooms
    })

@login_required
def get_notifications_list(request):
    """Get list of notifications for the current user"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]  # Get last 10 notifications
    
    return JsonResponse({
        'notifications': [{
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'link': notification.link,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'notification_type': notification.notification_type
        } for notification in notifications]
    })

class GenerateContractView(View):
    def post(self, request, *args, **kwargs):
        try:
            order_id = request.POST.get('order_id')
            if not order_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Order ID is required'
                }, status=400)

            # Validate file uploads
            id_document = request.FILES.get('id_document')
            selfie_photo = request.FILES.get('selfie_photo')
            
            if not id_document or not selfie_photo:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both ID document and selfie photo are required'
                }, status=400)

            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Order not found'
                }, status=404)

            # Check if contract already exists
            existing_contract = DigitalContract.objects.filter(order=order).first()
            if existing_contract:
                # Update verification documents if contract exists
                existing_contract.id_document = id_document
                existing_contract.selfie_photo = selfie_photo
                existing_contract.is_verified = False
                existing_contract.verified_by = None
                existing_contract.verified_at = None
                existing_contract.save()
                
                # Create notification for lender to verify
                create_notification(
                    user=order.product.user,
                    notification_type='verification_needed',
                    title='Identity Verification Required',
                    message=f'New verification documents uploaded for {order.product.title} rental',
                    link=f'/order/{order.ecommerce_id}'
                )

                return JsonResponse({
                    'status': 'success',
                    'message': 'Verification documents updated successfully. Awaiting lender verification.',
                    'contract_id': str(existing_contract.contract_id)
                })

            # Get user's name, fallback to username if full name is not set
            borrower_name = order.user.get_full_name() or order.user.username
            lender_name = order.product.user.get_full_name() or order.product.user.username

            # Create directory if it doesn't exist
            contract_dir = os.path.join(settings.MEDIA_ROOT, 'contracts')
            os.makedirs(contract_dir, exist_ok=True)

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"{settings.SITE_URL}/contract/verify/{order.id}/")
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")

            # Save QR code
            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_path = f'contracts/qr_{order.id}.png'
            default_storage.save(qr_path, ContentFile(qr_buffer.getvalue()))

            # Create contract with verification documents
            contract = DigitalContract.objects.create(
                order=order,
                lender_signature=lender_name,
                id_document=id_document,
                selfie_photo=selfie_photo
            )

            # Generate PDF using reportlab
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30
            )
            story.append(Paragraph("Rental Agreement", title_style))
            story.append(Spacer(1, 12))

            # Contract details
            story.append(Paragraph(f"Contract ID: {contract.contract_id}", styles['Normal']))
            story.append(Paragraph(f"Date: {contract.created_at.strftime('%B %d, %Y')}", styles['Normal']))
            story.append(Spacer(1, 12))

            # Parties
            story.append(Paragraph("PARTIES TO THE AGREEMENT", styles['Heading2']))
            story.append(Paragraph(f"Lender: {lender_name}", styles['Normal']))
            story.append(Paragraph(f"Borrower: {borrower_name}", styles['Normal']))
            story.append(Spacer(1, 12))

            # Item details
            story.append(Paragraph("ITEM DETAILS", styles['Heading2']))
            story.append(Paragraph(f"Item: {order.product.title}", styles['Normal']))
            story.append(Paragraph(f"Description: {order.product.description}", styles['Normal']))
            story.append(Spacer(1, 12))

            # Terms
            story.append(Paragraph("RENTAL TERMS", styles['Heading2']))
            story.append(Paragraph(f"Start Date: {order.rent_start.strftime('%B %d, %Y')}", styles['Normal']))
            story.append(Paragraph(f"End Date: {order.rent_end.strftime('%B %d, %Y')}", styles['Normal']))
            story.append(Paragraph(f"Rental Amount: ₹{order.total}", styles['Normal']))
            story.append(Paragraph(f"Security Deposit: ₹{order.security_deposit}", styles['Normal']))
            story.append(Spacer(1, 12))

            # Return Conditions
            story.append(Paragraph("RETURN CONDITIONS", styles['Heading2']))
            story.append(Paragraph("1. Item must be returned in the same condition as received", styles['Normal']))
            story.append(Paragraph("2. Any damage will be deducted from the security deposit", styles['Normal']))
            story.append(Paragraph("3. Late returns will incur additional charges", styles['Normal']))
            story.append(Spacer(1, 12))

            # Signatures
            story.append(Paragraph("SIGNATURES", styles['Heading2']))
            story.append(Paragraph(f"Lender Signature: {lender_name}", styles['Normal']))
            story.append(Paragraph("Borrower Signature: _________________", styles['Normal']))

            # Build PDF
            doc.build(story)

            # Save PDF with a unique filename
            pdf_filename = f'contract_{contract.contract_id}.pdf'
            pdf_path = f'contracts/{pdf_filename}'
            
            # Save the PDF file
            default_storage.save(pdf_path, ContentFile(buffer.getvalue()))
            
            # Update contract with PDF path
            contract.pdf_document = pdf_path
            contract.save()

            # Verify file was saved
            if default_storage.exists(pdf_path):
                # Get or create chat room
                chat_room, created = ChatRoom.objects.get_or_create(order=order)

                # Send via chat
                chat_message = ChatMessage.objects.create(
                    chat_room=chat_room,
                    sender=request.user,
                    message="Digital contract and verification documents uploaded. Awaiting lender verification."
                )

                # Create attachment for the contract PDF
                with default_storage.open(pdf_path, 'rb') as pdf_file:
                    attachment = ChatAttachment.objects.create(
                        message=chat_message,
                        file=File(pdf_file, name=pdf_filename),
                        file_type='document',
                        file_name=pdf_filename
                    )

                # Create notification for lender
                create_notification(
                    user=order.product.user,
                    notification_type='verification_needed',
                    title='Identity Verification Required',
                    message=f'New rental request with verification documents for {order.product.title}',
                    link=f'/order/{order.ecommerce_id}'
                )

                # Send email to lender
                email_body = f"""
Dear {lender_name},

A new rental request has been submitted for {order.product.title}.

The borrower has uploaded their verification documents and a digital contract has been generated.

Please review the following:
1. Verify the borrower's ID and selfie match
2. Check the contract details
3. Approve or reject the rental request

You can review the documents and contract through:
1. The chat section in the order details
2. The contract section in your dashboard
3. Direct link: {settings.SITE_URL}/order/{order.ecommerce_id}

Best regards,
WardrobeShare Team
                """

                try:
                    send_mail(
                        'Identity Verification Required - Action Needed',
                        email_body,
                        settings.DEFAULT_FROM_EMAIL,
                        [order.product.user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Error sending email: {str(e)}")
                    # Continue execution even if email fails

                return JsonResponse({
                    'status': 'success',
                    'message': 'Contract and verification documents uploaded successfully. Awaiting lender verification.',
                    'contract_id': str(contract.contract_id)
                })
            else:
                raise Exception("Failed to save contract PDF")

        except Exception as e:
            print(f"Error generating contract: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class AcceptContractView(View):
    def post(self, request, *args, **kwargs):
        try:
            contract_id = kwargs.get('contract_id')
            contract = DigitalContract.objects.get(contract_id=contract_id)
            
            if contract.order.user != request.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Unauthorized'
                }, status=403)
            
            signature = request.POST.get('signature')
            if not signature:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Signature is required'
                }, status=400)
            
            contract.borrower_signature = signature
            contract.borrower_accepted = True
            contract.accepted_at = timezone.now()
            contract.status = 'accepted'
            contract.save()
            
            # Send notification
            create_notification(
                user=contract.order.product.user,
                notification_type='contract_accepted',
                title='Contract Accepted',
                message=f'{contract.order.user.get_full_name()} has accepted the contract for {contract.order.product.title}',
                link=f'/order/{contract.order.ecommerce_id}'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Contract accepted successfully'
            })
            
        except DigitalContract.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Contract not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class UploadIDView(View):
    def post(self, request, *args, **kwargs):
        try:
            id_document = request.FILES.get('id_document')
            if not id_document:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No document uploaded'
                }, status=400)
            
            # Check if verification already exists
            if hasattr(request.user, 'id_verification'):
                return JsonResponse({
                    'status': 'error',
                    'message': 'ID verification already exists'
                }, status=400)
            
            # Create verification record
            verification = IDVerification.objects.create(
                user=request.user,
                id_document=id_document
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'ID document uploaded successfully',
                'verification_id': verification.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class VerifyIDView(View):
    def post(self, request, *args, **kwargs):
        try:
            user_id = kwargs.get('user_id')
            verification = IDVerification.objects.get(user_id=user_id)
            
            if not request.user.is_staff:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Unauthorized'
                }, status=403)
            
            verification.verified = True
            verification.verified_by = request.user
            verification.verified_at = timezone.now()
            verification.save()
            
            # Send notification to user
            create_notification(
                user=verification.user,
                notification_type='id_verified',
                title='ID Verification Complete',
                message='Your ID has been verified. You can now proceed with rentals.',
                link='/profile'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'ID verified successfully'
            })
            
        except IDVerification.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Verification not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class VerifyContractView(View):
    def get(self, request, order_id, *args, **kwargs):
        try:
            order = Order.objects.get(id=order_id)
            contract = order.digital_contract
            
            if not contract:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No contract found for this order'
                }, status=404)
            
            return JsonResponse({
                'status': 'success',
                'contract': {
                    'id': str(contract.contract_id),
                    'created_at': contract.created_at.strftime('%B %d, %Y'),
                    'status': contract.status,
                    'lender_accepted': contract.lender_accepted,
                    'borrower_accepted': contract.borrower_accepted,
                    'order': {
                        'id': order.id,
                        'product_title': order.product.title,
                        'start_date': order.rent_start.strftime('%B %d, %Y'),
                        'end_date': order.rent_end.strftime('%B %d, %Y'),
                        'total_amount': order.total,
                        'lender': order.product.user.get_full_name(),
                        'borrower': order.user.get_full_name()
                    }
                }
            })
            
        except Order.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Order not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class ViewContractView(View):
    def get(self, request, contract_id, *args, **kwargs):
        try:
            contract = DigitalContract.objects.get(contract_id=contract_id)
            
            # Check if user has permission to view the contract
            if request.user != contract.order.product.user and request.user != contract.order.user:
                return HttpResponseForbidden("You don't have permission to view this contract")
            
            # Get latest verification images related to this order's chat room
            chat_room = ChatRoom.objects.filter(order=contract.order).first()
            govt_verification = None
            selfie_verification = None
            if chat_room:
                govt_verification = VerificationRequest.objects.filter(
                    chat_room=chat_room,
                    type='govt_id',
                    id_document__isnull=False
                ).order_by('-created_at').first()
                
                selfie_verification = VerificationRequest.objects.filter(
                    chat_room=chat_room,
                    type='selfie',
                    selfie__isnull=False
                ).order_by('-created_at').first()
            
            context = {
                'contract': contract,
                'order': contract.order,
                'product': contract.order.product,
                'lender': contract.order.product.user,
                'borrower': contract.order.user,
                'govt_verification': govt_verification,
                'selfie_verification': selfie_verification,
            }
            
            return render(request, 'app/view_contract.html', context)
            
        except DigitalContract.DoesNotExist:
            return HttpResponseNotFound("Contract not found")
        except Exception as e:
            return HttpResponseServerError(str(e))

class DownloadContractView(View):
    def get(self, request, contract_id, *args, **kwargs):
        try:
            contract = DigitalContract.objects.get(contract_id=contract_id)
            
            # Check if user has permission to download the contract
            if request.user != contract.order.product.user and request.user != contract.order.user:
                return HttpResponseForbidden("You don't have permission to download this contract")
            
            # Generate PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="contract_{contract.contract_id}.pdf"'
            
            # Create PDF using reportlab
            p = canvas.Canvas(response)
            p.drawString(100, 750, f"Rental Contract - {contract.contract_id}")
            p.drawString(100, 700, f"Created: {contract.created_at.strftime('%B %d, %Y')}")
            p.drawString(100, 650, f"Status: {contract.get_status_display()}")
            p.drawString(100, 600, f"Lender: {contract.order.product.user.get_full_name()}")
            p.drawString(100, 550, f"Borrower: {contract.order.user.get_full_name()}")
            p.drawString(100, 500, f"Item: {contract.order.product.title}")
            p.drawString(100, 450, f"Rental Period: {contract.order.rent_start.strftime('%B %d, %Y')} to {contract.order.rent_end.strftime('%B %d, %Y')}")
            p.drawString(100, 400, f"Total Amount: ₹{contract.order.total}")
            
            # Add terms and conditions
            p.drawString(100, 350, "Terms and Conditions:")
            y = 300
            for term in contract.terms.split('\n'):
                p.drawString(120, y, term)
                y -= 20
            
            p.showPage()
            p.save()
            
            return response
            
        except DigitalContract.DoesNotExist:
            return HttpResponseNotFound("Contract not found")
        except Exception as e:
            return HttpResponseServerError(str(e))

@login_required
def borrower_dashboard(request):
    # Set user as borrower
    request.session['is_borrower'] = True
    request.session['is_lender'] = False
    
    today = datetime.now()
    
    # Get user's profile
    try:
        user_profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.error(request, 'Please complete your profile first')
        return redirect('/accounts/profile')
    
    # Overview Section
    active_rentals = Order.objects.filter(
        user=request.user,
        rental_status='approved'
    ).count()
    
    upcoming_pickups = Order.objects.filter(
        user=request.user,
        rental_status='approved',
        delivery_date__gte=today
    ).order_by('delivery_date')
    
    pending_requests = Order.objects.filter(
        user=request.user,
        rental_status='pending_approval'
    ).count()
    
    # Active Rentals Section
    active_rentals_details = Order.objects.filter(
        user=request.user,
        rental_status='approved'
    ).select_related('product', 'product__user').order_by('rent_end')
    
    # Rental Requests Status
    pending_requests_details = Order.objects.filter(
        user=request.user,
        rental_status='pending_approval'
    ).select_related('product', 'product__user')
    
    rejected_requests = Order.objects.filter(
        user=request.user,
        rental_status='declined'
    ).select_related('product', 'product__user')
    
    # Digital Contracts
    pending_contracts = DigitalContract.objects.filter(
        order__user=request.user,
        status='pending',
        borrower_accepted=False
    ).select_related('order', 'order__product', 'order__product__user', 'order__chatroom')
    
    # Past Rentals & Reviews
    past_rentals = Order.objects.filter(
        user=request.user,
        rental_status='approved',
        rent_end__lt=today
    ).select_related('product', 'product__user')
    
    # Get reviews left by the borrower
    reviews = Review.objects.filter(
        user=user_profile
    )
    
    context = {
        'active_rentals_count': active_rentals,
        'upcoming_pickups': upcoming_pickups,
        'pending_requests_count': pending_requests,
        'active_rentals': active_rentals_details,
        'pending_requests': pending_requests_details,
        'rejected_requests': rejected_requests,
        'pending_contracts': pending_contracts,
        'past_rentals': past_rentals,
        'reviews': reviews,
        'is_borrower': True,
        'user_profile': user_profile
    }
    
    return render(request, 'borrower/dashboard.html', context)

@login_required
def submit_review(request, rental_id):
    if request.method == 'POST':
        rental = get_object_or_404(Order, id=rental_id, borrower=request.user)
        
        # Check if review already exists
        if Review.objects.filter(order=rental).exists():
            messages.error(request, 'You have already submitted a review for this rental.')
            return redirect('borrower_dashboard')
            
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        Review.objects.create(
            order=rental,
            reviewer=request.user,
            reviewee=rental.lender,
            rating=rating,
            comment=comment
        )
        
        messages.success(request, 'Review submitted successfully!')
        return redirect('borrower_dashboard')
        
    return redirect('borrower_dashboard')

@login_required
def send_message(request):
    """API endpoint to send a new message"""
    try:
        data = json.loads(request.body)
        chat_id = data.get('chat_id')
        message_content = data.get('message')
        
        chat_room = get_object_or_404(ChatRoom, id=chat_id)
        
        # Verify user is either the lender or borrower
        if request.user not in [chat_room.order.user, chat_room.order.product.user]:
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
        # Create the message
        message = ChatMessage.objects.create(
            chat_room=chat_room,
            sender=request.user,
            message=message_content,
            message_type='text'
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'message': message.message,
                'message_type': message.message_type,
                'sender': {
                    'id': message.sender.id,
                    'username': message.sender.username
                },
                'timestamp': message.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def lender_dashboard(request):
    # Set user as lender
    request.session['is_lender'] = True
    request.session['is_borrower'] = False
    
    # Get all products for the lender
    products = Post.objects.filter(user=request.user)
    
    # Get active rentals
    active_rentals = Order.objects.filter(
        product__user=request.user,
        rental_status='approved'
    ).select_related('user', 'product')
    
    # Get pending rental requests
    pending_requests = Order.objects.filter(
        product__user=request.user,
        rental_status='pending_approval'
    ).select_related('user', 'product')
    
    # Calculate total earnings (from approved rentals that have ended)
    today = datetime.now()
    total_earnings = Order.objects.filter(
        product__user=request.user,
        rental_status='approved',
        rent_end__lt=today,
        payment_status=True
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Get reviews for the lender's products
    reviews = Review.objects.filter(
        profile__user=request.user
    ).select_related('user', 'profile').order_by('-created_at')
    
    # Calculate average rating
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Get digital contracts
    contracts = DigitalContract.objects.filter(
        order__product__user=request.user
    ).select_related('order', 'order__product', 'order__user')
    
    # Get product statistics
    product_stats = {}
    for product in products:
        views = ProductView.objects.filter(product=product).count()
        rental_interest = Order.objects.filter(product=product).count()
        product_stats[product.id] = {
            'views': views,
            'rental_interest': rental_interest
        }
    
    # Calculate days remaining for active rentals
    for rental in active_rentals:
        rental.days_remaining = (rental.rent_end - timezone.now().date()).days
    
    # Prepare overview data
    overview = {
        'total_earnings': total_earnings,
        'pending_requests': pending_requests.count(),
        'active_rentals': active_rentals.count(),
        'total_items': products.count()
    }
    
    # Prepare reviews data
    reviews_data = {
        'average_rating': avg_rating,
        'total_reviews': reviews.count(),
        'recent_reviews': reviews[:5]  # Get 5 most recent reviews
    }
    
    context = {
        'products': products,
        'active_rentals': active_rentals,
        'pending_requests': pending_requests,
        'overview': overview,
        'reviews': reviews_data,
        'contracts': contracts,
        'product_stats': product_stats,
        'is_lender': True
    }
    
    return render(request, 'app/lender_dashboard.html', context)

@login_required
def lender_contracts(request):
    # Set user as lender
    request.session['is_lender'] = True
    request.session['is_borrower'] = False
    
    # Get all contracts for the lender's products
    contracts = DigitalContract.objects.filter(
        order__product__user=request.user
    ).select_related(
        'order',
        'order__product',
        'order__user',
        'order__user__profile',
        'verified_by'
    ).order_by('-created_at')
    
    context = {
        'contracts': contracts,
        'is_lender': True
    }
    
    return render(request, 'app/lender_contracts.html', context)

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Post, id=product_id)
    return render(request, 'app/product_detail.html', {'product': product})

@login_required
def create_product(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            messages.success(request, 'Product created successfully')
            return redirect('lender_dashboard')
    else:
        form = PostForm()
    return render(request, 'app/product_form.html', {'form': form})

@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Post, id=product_id, user=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully')
            return redirect('lender_dashboard')
    else:
        form = PostForm(instance=product)
    return render(request, 'app/product_form.html', {'form': form, 'product': product})

@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Post, id=product_id, user=request.user)
    product.delete()
    messages.success(request, 'Product deleted successfully')
    return redirect('lender_dashboard')

@login_required
def create_order(request, product_id):
    product = get_object_or_404(Post, id=product_id)
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.product = product
            order.save()
            messages.success(request, 'Order created successfully')
            return redirect('my_orders')
    else:
        form = OrderForm()
    return render(request, 'app/order_form.html', {'form': form, 'product': product})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'app/my_orders.html', {'orders': orders})

@login_required
def search_products(request):
    query = request.GET.get('q', '')
    products = Post.objects.filter(availability=True).filter(
        Q(title__icontains=query) |
        Q(description__icontains=query)
    ).exclude(user=request.user)
    return render(request, 'app/search_results.html', {'products': products, 'query': query})

@login_required
def handle_request(request, order_id, action):
    order = get_object_or_404(Order, id=order_id, product__user=request.user)
    
    if action == 'approve':
        # Mark rental as approved so it shows up in active chats and dashboards
        order.rental_status = 'approved'
        order.save()
        # Create chat room for the order
        chat_room, created = ChatRoom.objects.get_or_create(
            order=order,
            defaults={'is_active': True}
        )
        # Create notification for the borrower
        Notification.objects.create(
            user=order.user,
            notification_type='rental_approved',
            title='Rental Request Approved',
            message=f'Your request for your item "{order.product.title}" is accepted! It\'s time to message and contact your lender.',
            link=f'/chat/{chat_room.id}/'
        )
        messages.success(request, 'Request approved successfully! Now you can send a digital contract and message the borrower.')
        return redirect('chat_room', chat_id=chat_room.id)
    elif action == 'decline':
        order.rental_status = 'declined'
        order.save()
        
        # Create notification for the borrower
        Notification.objects.create(
            user=order.user,
            notification_type='rental_declined',
            title='Rental Request Declined',
            message=f'Your rental request for {order.product.title} has been declined.',
            link=f'/order/{order.id}/'
        )
        
        return JsonResponse({'status': 'success', 'message': 'Request declined successfully'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid action'})

@login_required
def clear_all_notifications(request):
    """Clear all notifications for the current user"""
    if request.method == 'POST':
        Notification.objects.filter(user=request.user).delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)

@login_required
def digital_contract(request, chat_room_id):
    try:
        chat_room = ChatRoom.objects.get(id=chat_room_id)
        
        # Check if the user is the lender
        if request.user != chat_room.order.product.user:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('chat_room', chat_room_id=chat_room_id)
        
        # Get order details and contract with related fields
        order = chat_room.order
        contract = DigitalContract.objects.filter(order=order).first()
        
        # Get latest verification files for this chat room
        govt_verification = VerificationRequest.objects.filter(
            chat_room=chat_room,
            type='govt_id',
            id_document__isnull=False
        ).order_by('-created_at').first()
        
        selfie_verification = VerificationRequest.objects.filter(
            chat_room=chat_room,
            type='selfie',
            selfie__isnull=False
        ).order_by('-created_at').first()
        
        context = {
            'chat_room': chat_room,
            'order': order,
            'contract': contract,
            'govt_verification': govt_verification,
            'selfie_verification': selfie_verification,
            'today': timezone.now(),
        }
        
        return render(request, 'chat/digital_contract.html', context)
    except ChatRoom.DoesNotExist:
        messages.error(request, "Chat room not found.")
        return redirect('chat_list')

@login_required
def send_contract(request):
    if request.method == 'POST':
        try:
            chat_room_id = request.POST.get('chat_room_id')
            chat_room = ChatRoom.objects.get(id=chat_room_id)
            
            # Check if the user is the lender
            if request.user != chat_room.order.product.user:
                return JsonResponse({
                    'status': 'error',
                    'message': "You don't have permission to send contracts."
                }, status=403)
            
            # Get or create the digital contract
            contract, created = DigitalContract.objects.get_or_create(
                order=chat_room.order,
                defaults={
                    'lender_signature': chat_room.order.product.user.get_full_name() or chat_room.order.product.user.username,
                    'status': 'pending'
                }
            )
            
            # Update contract details (persisted on the contract itself)
            contract.rent_start = request.POST.get('start_date') or None
            contract.rent_end = request.POST.get('end_date') or None
            contract.rental_price = request.POST.get('rental_price') or None
            contract.contract_security_deposit = request.POST.get('security_deposit') or None
            contract.late_fees = request.POST.get('late_fees') or None
            contract.damage_penalties = request.POST.get('damage_penalties') or ''
            contract.additional_terms = request.POST.get('additional_terms') or ''
            contract.status = 'pending'  # Set status to pending for borrower acceptance
            contract.save()
            
            # Handle pre-lending images
            pre_lending_images = request.FILES.getlist('pre_lending_images')
            for image in pre_lending_images:
                PreLendingImage.objects.create(
                    order=chat_room.order,
                    image=image
                )
            
            # Create contract message
            contract_message = f"""
            Digital Contract for {chat_room.order.product.title}
            
            Rental Details:
            - Start Date: {contract.rent_start}
            - End Date: {contract.rent_end}
            - Rental Price: ₹{contract.rental_price}
            - Security Deposit: ₹{contract.security_deposit}
            
            Terms and Conditions:
            - Late Fees: ₹{contract.late_fees} per day
            - Damage Penalties: {contract.damage_penalties}
            - Additional Terms: {contract.additional_terms}
            
            Please review and accept the contract.
            """
            
            ChatMessage.objects.create(
                chat_room=chat_room,
                sender=request.user,
                message=contract_message,
                message_type='contract'
            )
            
            # Create notification for the borrower
            create_notification(
                user=chat_room.order.user,
                notification_type='contract_sent',
                title='Contract Sent',
                message=f'The lender has sent you a contract for {chat_room.order.product.title}',
                link=f'/chat/{chat_room.id}/contract/'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Contract sent successfully'
            })
            
        except ChatRoom.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Chat room not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@login_required
def accept_verification(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            verification_id = data.get('request_id')
            verification_type = data.get('type', 'govt_id')  # Default to govt_id if not specified
            
            verification = VerificationRequest.objects.get(id=verification_id)
            
            # Check if the user is the lender
            if request.user != verification.chat_room.order.product.user:
                return JsonResponse({
                    'success': False,
                    'error': 'You are not authorized to accept this verification'
                }, status=403)
            
            # Update the acceptance status
            verification.acceptance_status = 'accepted'
            verification.save()
            
            # Create notification for the borrower
            borrower = verification.chat_room.order.user
            create_notification(
                user=borrower,
                notification_type='verification_accepted',
                title='Verification Accepted',
                message=f'Your {verification_type} verification has been accepted by the lender.',
                link=f'/chat/{verification.chat_room.id}/'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{verification_type} verification accepted successfully'
            })
            
        except VerificationRequest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Verification request not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)

@login_required
def reject_verification(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            verification_id = data.get('request_id')
            verification_type = data.get('type')

            verification = get_object_or_404(VerificationRequest, id=verification_id)
            
            # Check if user is the lender
            if request.user != verification.chat_room.order.product.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Only the lender can reject verifications'
                }, status=403)

            # Update verification status
            verification.acceptance_status = 'rejected'
            verification.save()

            # Create notification for borrower
            create_notification(
                user=verification.chat_room.order.user,
                notification_type='verification_rejected',
                title='Verification Rejected',
                message=f'Your {verification_type} verification has been rejected',
                link=f'/chat/{verification.chat_room.id}/'
            )

            return JsonResponse({
                'success': True,
                'message': 'Verification rejected successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)

@require_POST
def accept_verification(request):
    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        verification_type = data.get('type')
        
        # Get the verification request
        verification = VerificationRequest.objects.get(id=request_id)
        
        # Check if the user is the lender
        if request.user != verification.chat_room.order.product.user:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
        # Update the acceptance status
        verification.acceptance_status = 'accepted'
        verification.save()
        
        # Create notification for the borrower
        create_notification(
            user=verification.chat_room.order.user,
            notification_type='verification_accepted',
            title='Verification Accepted',
            message=f'Your {verification_type} verification has been accepted',
            link=f'/chat/{verification.chat_room.id}/'
        )
        
        return JsonResponse({'success': True})
    except VerificationRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Verification request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def add_to_contract(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            verification_id = data.get('verification_id')
            verification_type = data.get('type')
            
            # Get the verification request
            verification = VerificationRequest.objects.get(id=verification_id)
            
            # Check if user is the lender
            if request.user != verification.chat_room.order.product.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Only the lender can add verifications to the contract'
                }, status=403)
            
            # Check if verification is accepted
            if verification.acceptance_status != 'accepted':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Only accepted verifications can be added to the contract'
                }, status=400)
            
            # Get or create the digital contract
            contract, created = DigitalContract.objects.get_or_create(
                order=verification.chat_room.order,
                defaults={
                    'lender_signature': verification.chat_room.order.product.user.get_full_name() or verification.chat_room.order.product.user.username,
                    'status': 'draft'
                }
            )
            
            # Update the contract with the verification document
            if verification_type == 'govt_id' and verification.id_document:
                from django.core.files import File
                from django.core.files.storage import default_storage
                import os
                
                # Get the file extension
                _, ext = os.path.splitext(verification.id_document.name)
                # Create a new filename
                new_filename = f'documents/verification/{timezone.now().strftime("%Y/%m")}/ids/govt_id_{verification.id}{ext}'
                
                # Copy the file using default_storage
                with verification.id_document.open('rb') as source_file:
                    # Save the file to the new location
                    new_path = default_storage.save(new_filename, source_file)
                    # Update the contract's id_document field
                    contract.id_document.name = new_path
                    contract.save()
                
                # Create a chat message about the ID being added to contract
                ChatMessage.objects.create(
                    chat_room=verification.chat_room,
                    sender=request.user,
                    message=f"Government ID has been added to the contract.",
                    message_type='system'
                )
            elif verification_type == 'selfie' and verification.selfie:
                from django.core.files import File
                from django.core.files.storage import default_storage
                import os
                
                # Get the file extension
                _, ext = os.path.splitext(verification.selfie.name)
                # Create a new filename
                new_filename = f'documents/verification/{timezone.now().strftime("%Y/%m")}/selfies/selfie_{verification.id}{ext}'
                
                # Copy the file using default_storage
                with verification.selfie.open('rb') as source_file:
                    # Save the file to the new location
                    new_path = default_storage.save(new_filename, source_file)
                    # Update the contract's selfie_photo field
                    contract.selfie_photo.name = new_path
                    contract.save()
                
                # Create a chat message about the selfie being added to contract
                ChatMessage.objects.create(
                    chat_room=verification.chat_room,
                    sender=request.user,
                    message=f"Selfie photo has been added to the contract.",
                    message_type='system'
                )
            
            # Create notification for the borrower
            create_notification(
                user=verification.chat_room.order.user,
                notification_type='contract_updated',
                title='Contract Updated',
                message=f'The lender has added your {verification_type.replace("_", " ")} to the contract.',
                link=f'/chat/{verification.chat_room.id}/'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Verification added to contract successfully'
            })
            
        except VerificationRequest.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Verification request not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@login_required
def accept_contract(request, contract_id):
    """Accept a digital contract"""
    try:
        contract = DigitalContract.objects.get(contract_id=contract_id)
        
        # Get data from request
        data = json.loads(request.body)
        signature = data.get('signature', '').strip()
        acceptance = data.get('acceptance', '').strip()
        is_lender = request.user == contract.order.product.user
        
        # Handle lender approval
        if is_lender:
            action = data.get('action', '').strip()
            if action not in ['approve', 'reject']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid action. Must be either approve or reject.'
                }, status=400)
                
            # Update contract status based on lender's action
            if action == 'approve':
                contract.lender_approved = True
                contract.lender_signature = request.user.get_full_name() or request.user.username
                contract.lender_approval_date = timezone.now()
                contract.status = 'pending_borrower'
                message = 'Contract approved by lender'
                notification_type = 'contract_approved'
            else:  # reject
                contract.lender_approved = False
                contract.status = 'rejected'
                message = 'Contract rejected by lender'
                notification_type = 'contract_rejected'
            
            contract.save()
            
            # Create notification for borrower
            create_notification(
                user=contract.order.user,
                notification_type=notification_type,
                title='Contract ' + ('Approved' if action == 'approve' else 'Rejected'),
                message=f'The lender has {action}d the contract for {contract.order.product.title}',
                link=f'/contract/view/{contract.contract_id}'
            )
            
            # Create chat message
            ChatMessage.objects.create(
                chat_room=ChatRoom.objects.get(order=contract.order),
                sender=request.user,
                message=message,
                message_type='system'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': message
            })
        
        # Handle borrower acceptance
        else:
            # Check if lender has approved the contract
            if not contract.lender_approved:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Contract must be approved by the lender first'
                }, status=400)
            
            # Validate signature and acceptance
            if not signature or not acceptance:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please provide both your name and acceptance'
                }, status=400)
                
            # Check if acceptance is "I ACCEPT"
            if acceptance.upper() != 'I ACCEPT':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please type "I ACCEPT" to confirm'
                }, status=400)
            
            # Update contract
            contract.borrower_signature = signature
            contract.status = 'accepted'
            contract.accepted_at = timezone.now()
            contract.save()
            
            # Create notification for lender
            create_notification(
                user=contract.order.product.user,
                notification_type='contract_accepted',
                title='Contract Accepted',
                message=f'The borrower has accepted the contract for {contract.order.product.title}',
                link=f'/contract/view/{contract.contract_id}'
            )
            
            # Create chat message
            ChatMessage.objects.create(
                chat_room=ChatRoom.objects.get(order=contract.order),
                sender=request.user,
                message='Contract accepted by borrower',
                message_type='system'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Contract accepted successfully'
            })
            
    except DigitalContract.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Contract not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def download_contract(request, contract_id):
    """Download a digital contract as PDF"""
    try:
        contract = DigitalContract.objects.get(contract_id=contract_id)
        
        # Check if user is authorized to view this contract
        if request.user not in [contract.order.user, contract.order.product.user]:
            return JsonResponse({
                'status': 'error',
                'message': 'You are not authorized to download this contract'
            }, status=403)
        
        # Generate PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="contract_{contract.contract_id}.pdf"'
        
        # Create PDF
        p = canvas.Canvas(response)
        p.drawString(100, 800, f"Digital Contract - {contract.contract_id}")
        p.drawString(100, 780, f"Product: {contract.order.product.title}")
        p.drawString(100, 760, f"Borrower: {contract.order.user.username}")
        p.drawString(100, 740, f"Lender: {contract.order.product.user.username}")
        p.drawString(100, 720, f"Status: {contract.status}")
        p.drawString(100, 700, f"Created: {contract.created_at}")
        if contract.accepted_at:
            p.drawString(100, 680, f"Accepted: {contract.accepted_at}")
        
        # Add rental details
        p.drawString(100, 650, "Rental Details:")
        p.drawString(120, 630, f"Start Date: {contract.start_date}")
        p.drawString(120, 610, f"End Date: {contract.end_date}")
        p.drawString(120, 590, f"Rental Price: ${contract.rental_price}")
        p.drawString(120, 570, f"Security Deposit: ${contract.security_deposit}")
        p.drawString(120, 550, f"Late Fees: ${contract.late_fees}")
        p.drawString(120, 530, f"Damage Penalties: ${contract.damage_penalties}")
        
        # Add signatures
        p.drawString(100, 500, "Signatures:")
        if contract.borrower_signature:
            p.drawString(120, 480, f"Borrower: {contract.borrower_signature}")
            p.drawString(120, 460, f"Signed on: {contract.accepted_at}")
        
        p.showPage()
        p.save()
        
        return response
        
    except DigitalContract.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Contract not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def my_items(request):
    # Get all items posted by the current user
    items = Post.objects.filter(user=request.user).order_by('-updated_at')
    
    return render(request, 'app/my_items.html', {
        'items': items
    })

@login_required
def delete_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        post = Post.objects.get(id=post_id, user=request.user)
        post.delete()
        return JsonResponse({'success': True})
    except Post.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Post not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})