"""
URL configuration for wardobe project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from app.views import *
from app.verification_views import request_verification, submit_verification, set_rental_terms, delete_verification

urlpatterns = [
    path('main/', admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("app.urls")),
    
    # Media files serving
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
        'show_indexes': True,
    }),
    
    # Static files serving
    re_path(r'^static/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT,
        'show_indexes': True,
    }),

    # Chat URLs
    path('chats/', active_chats, name='active_chats'),
    path('chat/<int:chat_id>/', chat_room, name='chat_room'),
    path('chat/<int:chat_id>/messages/', get_chat_messages, name='get_chat_messages'),
    
    # Verification URLs
    path('chat/request-verification/', request_verification, name='request_verification'),
    path('chat/submit-verification/', submit_verification, name='submit_verification'),
    path('chat/delete-verification/', delete_verification, name='delete_verification'),
    path('chat/set-rental-terms/', set_rental_terms, name='set_rental_terms'),
]

# Add media serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
