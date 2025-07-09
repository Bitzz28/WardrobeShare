from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from .views import update_order
from .models import *
from .forms import *
@user_passes_test(lambda u:u.is_superuser)
def dashboard(r):
    return render(r,'admin/home.html')
#category
@user_passes_test(lambda u:u.is_superuser)
def category(r):
    form=CategoryForm()
    data=Category.objects.all()
    if r.method=="POST":
        form=CategoryForm(r.POST,r.FILES)
        if form.is_valid():
            form.save()
            return redirect('/admin/category')
    return render(r,'admin/category.html',{"form":form,"data":data})

@user_passes_test(lambda u:u.is_superuser)
def category_edit(r,id):
    data=Category.objects.get(id=id)
    items=Category.objects.all()
    form=CategoryForm(instance=data)
    if r.method=="POST":
        form=CategoryForm(r.POST,r.FILES,instance=data)
        if form.is_valid():
            form.save()
            return redirect('/admin/category')
    return render(r,'admin/category.html',{"form":form,"data":items})

@user_passes_test(lambda u:u.is_superuser)
def category_delete(r,id):
    try:
        Category.objects.get(id=id).delete()
    except:
        pass
    return redirect('/admin/category')
#slider   
@user_passes_test(lambda u:u.is_superuser)
def slider(r):
    form=SliderForm()
    slides=Slider.objects.all()
    if r.method=="POST":
        form=SliderForm(data=r.POST,files=r.FILES)
        if form.is_valid():
            form.save()
            return redirect('/admin/slider')
    return render(r,"admin/slider.html",{"form":form,"data":slides})
@user_passes_test(lambda u:u.is_superuser)
def slider_edit(r,id):
    data=Slider.objects.get(id=id)
    items=Slider.objects.all()
    form=SliderForm(instance=data)
    if r.method=="POST":
        form=SliderForm(r.POST,r.FILES,instance=data)
        if form.is_valid():
            form.save()
            return redirect('/admin/slider')
    return render(r,'admin/slider.html',{"form":form,"data":items})

@user_passes_test(lambda u:u.is_superuser)
def slider_delete(r,id):
    try:
        Slider.objects.get(id=id).delete()
    except:
        pass
    return redirect('/admin/slider')
#orders
@user_passes_test(lambda u:u.is_superuser)
def orders(r):
    order=Order.objects.filter(order_status=True).order_by("-id")
    return render(r,'admin/orders.html',{"data":order})
@user_passes_test(lambda u:u.is_superuser)
def updateorder(r,id):
    orders=Order.objects.filter(order_status=True).order_by("-id")
    order=Order.objects.get(id=id)
    if  order.delivery_status=="Pending":
        messages.error(r,'Seller has not confirmed the order yet')
        return redirect('/admin/orders')
    if  order.delivery_status=="Cancelled":
        messages.error(r,'Seller has cancelled the order')
        return redirect('/admin/orders')
    form=OrderForm(instance=order)
    if r.method=="POST":
        form=OrderForm(r.POST,instance=order)
        if form.is_valid():
            form.save()
            update_order(order.ecommerce_id,order.payment_id,order.payment_status)
            return redirect(f'/admin/orders')

    return render(r,'admin/orders.html',{"form":form,"data":orders})
import razorpay
@user_passes_test(lambda u:u.is_superuser)
def transactions(r):
    client = razorpay.Client(auth=("rzp_test_euB1g3Ioe7wejB", "k0phaX9LIQtibmploFiUPjs0"))
    payments = client.payment.all({"count":10})
    return render(r,'admin/transactions.html',{"data":payments["items"]})
@user_passes_test(lambda u:u.is_superuser)
def users(r):
    data=Profile.objects.all()
    return render(r,'admin/users.html',{"data":data})
@user_passes_test(lambda u:u.is_superuser)
def reviews(r):
    data=Comment.objects.order_by("-id")
    return render(r,'admin/reviews.html',{"data":data})
@user_passes_test(lambda u:u.is_superuser)
def review_delete(r,id):
    try:
        Comment.objects.get(id=id).delete()
    except:
        pass
    return redirect('/admin/reviews')