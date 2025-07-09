from django.contrib import admin

# Register your models here.
from .models import *
admin.site.register(Category)
admin.site.register(Profile)
admin.site.register(Comment)
admin.site.register(Post)
admin.site.register(Order)
admin.site.register(Review)