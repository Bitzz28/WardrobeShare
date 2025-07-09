from .models import *
from django import forms
from django.forms.models import inlineformset_factory
from datetime import datetime,date
import re
import uuid
style={'text': 'shadow-sm bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light',
       'image':'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400',
      'checkbox':'w-4 h-4 border border-gray-300 rounded bg-gray-50 focus:ring-3 focus:ring-blue-300 dark:bg-gray-700 dark:border-gray-600 dark:focus:ring-blue-600 dark:ring-offset-gray-800 dark:focus:ring-offset-gray-800', 
      }

class CategoryForm(forms.ModelForm):
    class Meta:
        model=Category
        fields='__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class':style['image']})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class':style['text'],'rows':3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class':style['checkbox']})
            else:
                field.widget.attrs.update({'class':style['text']})
class ProfileForm(forms.ModelForm):
    class Meta:
        model=Profile
        fields=['first_name','last_name','image','phone_number','city','address','profile_link']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class':style['image']})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class':style['text'],'rows':3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class':style['checkbox']})
            else:
                field.widget.attrs.update({'class':style['text']})
    def clean_phone_number(self):
        m=self.cleaned_data.get('phone_number')
        if re.match(r'^\d{10}$',m):
            return m
        else:
            raise forms.ValidationError("Enter valid number")
    def clean_profile_link(self):
        profile_link = self.cleaned_data.get('profile_link')
        if not profile_link:
            profile_link = str(uuid.uuid4())[:8]
        return profile_link
class PostForm(forms.ModelForm):
    class Meta:
        model=Post
        fields=['title','category','description','image','quantity','price',
                'gender','size', 'color', 'brand','rent_method','availability',
                'period','location','latitude','longitude','security_deposit']
        widgets = {
            'period': forms.DateInput(attrs={'type': 'date',}),
            'latitude': forms.NumberInput(attrs={'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000001'}),
            'security_deposit': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class':style['image']})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class':style['text'],'rows':3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class':style['checkbox']})
            else:
                field.widget.attrs.update({'class':style['text']})
        
        # Add help text for fields
        self.fields['brand'].help_text = "Enter the brand name of your item (optional)"
        self.fields['size'].help_text = "Select the size of your item"
        self.fields['security_deposit'].help_text = "Enter security deposit amount (optional)"
        self.fields['security_deposit'].required = False
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
    
    def clean_price(self):
        m=self.cleaned_data.get('price')
        if m>0:
            return m
        else:
            raise forms.ValidationError("Price should be greater than 0")
    
    def clean_quantity(self):
        m=self.cleaned_data.get('quantity')
        if m>0:
            return m
        else:
            raise forms.ValidationError("Quantity should be greater than 0")
    
    def clean_security_deposit(self):
        deposit = self.cleaned_data.get('security_deposit')
        if deposit is not None and deposit < 0:
            raise forms.ValidationError("Security deposit cannot be negative")
        return deposit
        
    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('latitude')
        lon = cleaned_data.get('longitude')
        
        if lat is not None and (lat < -90 or lat > 90):
            self.add_error('latitude', 'Latitude must be between -90 and 90')
            
        if lon is not None and (lon < -180 or lon > 180):
            self.add_error('longitude', 'Longitude must be between -180 and 180')
            
        return cleaned_data
class CommentForm(forms.ModelForm):
    class Meta:
        model=Comment
        fields=['subject','comment','image','rating']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class':style['image']})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class':style['text'],'rows':3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class':style['checkbox']})
            else:
                field.widget.attrs.update({'class':style['text']})    
class ReviewForm(forms.ModelForm):
    class Meta:
        model=Review
        fields=['subject','comment','image','rating']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class':style['image']})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class':style['text'],'rows':3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class':style['checkbox']})
            else:
                field.widget.attrs.update({'class':style['text']})    
class MakeOrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['rent_start', 'rent_end', 'full_name', 'mobile_no', 'alternate_no']
        widgets = {
            'rent_start': forms.DateInput(attrs={'type': 'date', 'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-teal-500 focus:border-teal-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white'}),
            'rent_end': forms.DateInput(attrs={'type': 'date', 'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-teal-500 focus:border-teal-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white'}),
            'full_name': forms.TextInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-teal-500 focus:border-teal-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white'}),
            'mobile_no': forms.TextInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-teal-500 focus:border-teal-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white'}),
            'alternate_no': forms.TextInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-teal-500 focus:border-teal-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white', 'required': False}),
        }
        labels = {
            'rent_start': 'From Date',
            'rent_end': 'To Date',
            'full_name': 'Full Name',
            'mobile_no': 'Mobile Number',
            'alternate_no': 'Alternate Number (Optional)',
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class':style['image']})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class':style['text'],'rows':3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class':style['checkbox']})
            else:
                field.widget.attrs.update({'class':style['text']})
    def clean_mobile_no(self):
        m=self.cleaned_data.get('mobile_no')
        if re.match(r'^\d{10}$',m):
            return m
        else:
            raise forms.ValidationError("Enter valid number")
class OrderForm(forms.ModelForm):
    class Meta:
        model=Order
        fields=['delivery_date','delivery_status']
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date',}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class':style['image']})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class':style['text'],'rows':3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class':style['checkbox']})
            else:
                field.widget.attrs.update({'class':style['text']})
class SliderForm(forms.ModelForm):
    class Meta:
        model=Slider
        fields='__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class':style['image']})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class':style['text'],'rows':3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class':style['checkbox']})
            else:
                field.widget.attrs.update({'class':style['text']})