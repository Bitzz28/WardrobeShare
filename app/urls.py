from django.contrib import admin
from django.urls import path,include
from . import views
from . import admin_views
from .verification_views import request_verification, submit_verification, set_rental_terms

urlpatterns = [
    path('',views.home, name='home'),
    path('accounts/profile/',views.profile, name='account_profile'),

    # My Items URLs
    path('lender/my-items/', views.my_items, name='my_items'),
    path('post/delete/<int:post_id>/', views.delete_post, name='delete_post'),

    path('post/add/',views.new_post),
    path('post/edit/<id>/',views.editpost),
    path('post/delete/<id>/',views.deletepost),
    path('post/view/<id>/',views.view_post, name='post_view'),
    path('post/all/',views.user_posts),
    path('user/posts/', views.user_posts, name='user_posts'),
    path('lender/dashboard/', views.lender_dashboard, name='lender_dashboard'),
    path('post/orders/',views.user_orders),
    path('user/orders/',views.user_orders),
    path('post/order/update/confirm/<id>/',views.user_orders_confirm),
    path('post/order/update/cancel/<id>/',views.user_orders_cancel),
    path('post/order/update/<id>/',views.user_orders_update),
    path('post/profile/<id>/',views.post_profile),
    path('post/reviews/',views.post_reviews),
    path('profile/reviews/',views.profile_reviews),

    path('search/',views.search, name='search'),

    #orders
    path('orders',views.orders),
    path('order/<int:id>/',views.orderdetails),
    path('order/<str:ecommerce_id>/',views.orderdetails),
    path('order/<int:id>/<int:q>/',views.makeorder),
    path('order/cancel/<int:id>',views.cancelorder),
    path('order/return/<int:id>',views.approve_return, name='approve_return'),
    path('order/payment/<str:id>/',views.orderpayment),
    
    path('order/payment/success/<str:pay>/<str:id>',views.paysuccess),
    path('order/payment/failed/<str:pay>/<str:id>',views.payfailed),

    #admin
    path('admin/',admin_views.dashboard),
    path('admin/category/',admin_views.category),
    path('admin/category/edit/<id>/',admin_views.category_edit),
    path('admin/category/delete/<id>/',admin_views.category_delete),
    path('admin/slider/',admin_views.slider),
    path('admin/slider/edit/<id>/',admin_views.slider_edit),
    path('admin/slider/delete/<id>/',admin_views.slider_delete),
    path('admin/reviews',admin_views.reviews),
    path('admin/review/delete/<id>/',admin_views.review_delete),

    path('admin/transactions/',admin_views.transactions),
    path('admin/users/',admin_views.users),

    #orders
    path('admin/orders/',admin_views.orders),
    path('admin/order/update/<int:id>/',admin_views.updateorder),

    path('profile/<str:profile_link>/', views.view_profile_by_link, name='view_profile_by_link'),

    # Lender order management
    path('lender/orders/', views.lender_orders, name='lender_orders'),
    path('lender/order/<int:order_id>/<str:action>/', views.handle_request, name='handle_request'),
    path('lender/contracts/', views.lender_contracts, name='lender_contracts'),

    # Notification URLs
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/list/', views.get_notifications_list, name='get_notifications_list'),
    path('notifications/unread-count/', views.get_unread_notifications_count, name='get_unread_notifications_count'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/clear-all/', views.clear_all_notifications, name='clear_all_notifications'),

    path('borrower/dashboard/', views.borrower_dashboard, name='borrower_dashboard'),
    path('review/submit/<int:rental_id>/', views.submit_review, name='submit_review'),

    # Chat URLs
    path('chat/<int:chat_id>/', views.chat_room, name='chat_room'),
    path('get_chat_messages/<int:chat_id>/<int:last_message_id>/', views.get_chat_messages, name='get_chat_messages'),
    path('send_message/', views.send_message, name='send_message'),
    path('chat/active/', views.active_chats, name='active_chats'),
    path('chat/unread-count/', views.get_unread_messages_count, name='get_unread_messages_count'),

    # Digital Contract URLs
    path('contract/generate/', views.GenerateContractView.as_view(), name='generate_contract'),
    path('contract/view/<uuid:contract_id>/', views.ViewContractView.as_view(), name='view_contract'),
    path('contract/accept/<uuid:contract_id>/', views.accept_contract, name='accept_contract'),
    path('contract/download/<uuid:contract_id>/', views.DownloadContractView.as_view(), name='download_contract'),
    
    # ID Verification URLs
    path('id/upload/', views.UploadIDView.as_view(), name='upload_id'),
    path('id/verify/<int:user_id>/', views.VerifyIDView.as_view(), name='verify_id'),

    path('chat/request-verification/', request_verification, name='request_verification'),
    path('chat/submit-verification/', submit_verification, name='submit_verification'),
    path('chat/set-rental-terms/', set_rental_terms, name='set_rental_terms'),
    path('accept_verification/', views.accept_verification, name='accept_verification'),
    path('reject_verification/', views.reject_verification, name='reject_verification'),

    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/create/', views.create_product, name='create_product'),
    path('product/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('product/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('order/create/<int:product_id>/', views.create_order, name='create_order'),
    path('orders/', views.my_orders, name='my_orders'),
    path('search/', views.search_products, name='search_products'),

    path('chat/<int:chat_room_id>/contract/', views.digital_contract, name='digital_contract'),
    path('send-contract/', views.send_contract, name='send_contract'),

    path('add-to-contract/', views.add_to_contract, name='add_to_contract'),
    
    # Pickup Schedule URLs - Commented out as views are not implemented yet
    # path('pickup/schedule/<int:chat_room_id>/', views.create_pickup_schedule, name='create_pickup_schedule'),
    # path('pickup/accept/<int:schedule_id>/', views.accept_pickup_schedule, name='accept_pickup_schedule'),
    # path('pickup/reschedule/<int:schedule_id>/', views.reschedule_pickup, name='reschedule_pickup'),
]