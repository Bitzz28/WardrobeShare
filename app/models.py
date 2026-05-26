from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import datetime
import uuid
from django.urls import reverse

# Define choices
delivery_choices = (
    ("Self Pickup", "Self Pickup"),
    ("Pending", "Pending"),
    ("Confirmed", "Confirmed"),
    ("Cancelled", "Cancelled"),
    ("Delivered", "Delivered"),
    ("Returned", "Returned"),
    ("Refunded", "Refunded"),
    ("Refund Cancel", "Refund Cancel")
)

# Create your models here.
class Profile(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    image=models.ImageField(upload_to="profiles",blank=True,null=True)
    first_name=models.CharField(max_length=50)
    last_name=models.CharField(max_length=50)
    phone_number=models.CharField(max_length=10)
    city=models.CharField(max_length=30)
    address=models.TextField()
    wallet=models.FloatField(default=0)
    profile_link=models.CharField(max_length=50, unique=True, blank=True)
    def __str__(self):
        return self.user.username
class Category(models.Model):
    name=models.CharField(max_length=50)
    image=models.ImageField(upload_to='categories')
    description=models.TextField(blank=True, null=True)
    def __str__(self):
        return self.name
class Slider(models.Model):
    image=models.ImageField(upload_to="slider")
    redirect_url=models.URLField()
class Post(models.Model):
    SIZE_CHOICES = (
        ("XS", "XS"),
        ("S", "S"),
        ("M", "M"),
        ("L", "L"),
        ("XL", "XL"),
        ("XXL", "XXL"),
        ("XXXL", "XXXL"),
        ("4XL", "4XL"),
        ("5XL", "5XL"),
        ("6XL", "6XL"),
        ("7XL", "7XL"),
        ("8XL", "8XL"),
        ("9XL", "9XL"),
        ("10XL", "10XL"),
        ("Free Size", "Free Size"),
        ("Custom Size", "Custom Size"),
    )
    GENDER_CHOICES = (
        ("Male", "Male"),
        ("Female", "Female"),
        ("Unisex", "Unisex"),
    )
    CONDITION_CHOICES = (
        ("New", "New"),
        ("Like New", "Like New"),
        ("Good", "Good"),
        ("Fair", "Fair"),
    )
    RENT_METHOD_CHOICES = (
        ("Day", "Per Day"),
        ("Week", "Per Week"),
        ("Month", "Per Month"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.FloatField()
    image = models.ImageField(upload_to="posts")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default="M")
    brand = models.CharField(max_length=50, default="Unknown")
    color = models.CharField(max_length=50, choices=(
        ("Black", "Black"),
        ("White", "White"),
        ("Red", "Red"),
        ("Blue", "Blue"),
        ("Green", "Green"),
        ("Yellow", "Yellow"),
        ("Pink", "Pink"),
        ("Purple", "Purple"),
        ("Orange", "Orange"),
        ("Brown", "Brown"),
        ("Grey", "Grey"),
        ("Multi", "Multi-color"),
    ), default="Black")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="Good")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="Unisex")
    rent_method = models.CharField(max_length=10, choices=RENT_METHOD_CHOICES, default="Day")
    period = models.DateField()
    quantity = models.IntegerField(default=1)
    availability = models.BooleanField(default=True)
    location = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    delivery_type = models.CharField(max_length=20, default="Self Pickup", editable=False)
    security_deposit = models.FloatField(null=True, blank=True, help_text="Optional security deposit amount required from borrower")
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.title
class PostImage(models.Model):
    post=models.ForeignKey(Post,on_delete=models.CASCADE)
    image=models.ImageField(upload_to="posts")
class Comment(models.Model):
    post=models.ForeignKey(Post,on_delete=models.CASCADE)
    user = models.ForeignKey(Profile,on_delete=models.CASCADE)  
    subject=models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    comment=models.TextField()
    empty=models.CharField(max_length=10,blank=True,null=True)
    image=models.ImageField(upload_to='comments',null=True,blank=True)
    rating=models.CharField(choices=(("1","1"),("12","2"),("123","3"),("1234","4"),("12345","5")),max_length=5)
class Review(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reviews_received')  
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reviews_given')  
    subject=models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    comment=models.TextField()
    empty=models.CharField(max_length=10,blank=True,null=True)
    image=models.ImageField(upload_to='comments',null=True,blank=True)
    rating=models.CharField(choices=(("1","1"),("12","2"),("123","3"),("1234","4"),("12345","5")),max_length=5)
class Order(models.Model):
    RENTAL_STATUS_CHOICES = [
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]
    
    ecommerce_id = models.UUIDField(default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=100)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    order_status = models.BooleanField(default=False)
    payment_status = models.BooleanField(default=False)
    rental_status = models.CharField(max_length=20, choices=RENTAL_STATUS_CHOICES, default='pending_approval')
    delivery_status = models.CharField(max_length=20, choices=delivery_choices, default="Pending")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Post, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    amount = models.FloatField(default=0.0)
    subtotal = models.FloatField(default=0.0)
    # platform_fee = models.FloatField(default=0.0)  # Removed from project
    security_deposit = models.FloatField(default=0.0)
    total = models.FloatField(default=0.0)
    full_name = models.CharField(max_length=100)
    mobile_no = models.CharField(max_length=10)
    alternate_no = models.CharField(max_length=10, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    rent_start = models.DateField()
    rent_end = models.DateField()
    qrcode = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    funds_released = models.BooleanField(default=False)
class DeliveryType(models.Model):
    name = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-truck')
    
    def __str__(self):
        return self.name
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('rental_approved', 'Rental Request Approved'),
        ('rental_declined', 'Rental Request Declined'),
        ('payment_received', 'Payment Received'),
        ('order_status', 'Order Status Update'),
        ('new_message', 'New Message'),
        ('chat_enabled', 'Chat Enabled'),
        ('contract_generated', 'Contract Generated'),
        ('contract_accepted', 'Contract Accepted')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)  # URL to redirect when clicked
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class ChatRoom(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Chat for Order {self.order.order_id}"

class ChatMessage(models.Model):
    MESSAGE_TYPES = (
        ('text', 'Text Message'),
        ('verification_request', 'Verification Request'),
        ('verification_submitted', 'Verification Submitted'),
        ('contract_generated', 'Contract Generated'),
        ('contract_signed', 'Contract Signed')
    )
    
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    message_type = models.CharField(max_length=50, choices=MESSAGE_TYPES, default='text')
    metadata = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        # Only return the actual message content for text messages
        if self.message_type == 'text':
            return self.message
        return f"{self.get_message_type_display()}"

class ChatAttachment(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(
        upload_to='documents/chat_attachments/%Y/%m/',
        null=True,
        blank=True,
        help_text='Uploaded chat attachments'
    )
    file_type = models.CharField(max_length=20, choices=[
        ('image', 'Image'),
        ('document', 'Document'),
        ('outfit_details', 'Outfit Details')
    ])
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    occasion_type = models.CharField(max_length=50, null=True, blank=True)
    style_notes = models.TextField(null=True, blank=True)
    care_instructions = models.TextField(null=True, blank=True)
    measurements = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Chat Attachment'
        verbose_name_plural = 'Chat Attachments'

    def __str__(self):
        return f"{self.file_type} attachment for message {self.message.id}"

class DigitalContract(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    )
    
    contract_id = models.UUIDField(default=uuid.uuid4, unique=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='digital_contract')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    # Contract Document
    pdf_document = models.FileField(
        upload_to='documents/contracts/%Y/%m/',
        validators=[FileExtensionValidator(['pdf'])],
        null=True,
        blank=True,
        help_text='PDF format only'
    )
    
    # Verification Documents
    id_document = models.ImageField(
        upload_to='documents/verification/%Y/%m/ids/',
        null=True,
        blank=True,
        help_text='Clear photo of government-issued ID'
    )
    selfie_photo = models.ImageField(
        upload_to='documents/verification/%Y/%m/selfies/',
        null=True,
        blank=True,
        help_text='Clear selfie with ID'
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_contracts'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Rental & financial terms
    rent_start = models.DateField(null=True, blank=True)
    rent_end = models.DateField(null=True, blank=True)
    rental_price = models.FloatField(null=True, blank=True)
    contract_security_deposit = models.FloatField(
        null=True,
        blank=True,
        help_text='Security deposit amount agreed in this contract'
    )
    late_fees = models.FloatField(
        null=True,
        blank=True,
        help_text='Late fee per day'
    )
    damage_penalties = models.TextField(
        null=True,
        blank=True,
        help_text='Description of damage penalties'
    )
    additional_terms = models.TextField(
        null=True,
        blank=True,
        help_text='Any additional terms or conditions'
    )
    
    # Signatures
    lender_signature = models.CharField(max_length=100, null=True, blank=True)
    borrower_signature = models.CharField(max_length=100, null=True, blank=True)
    borrower_accepted = models.BooleanField(default=False)
    lender_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Digital Contract'
        verbose_name_plural = 'Digital Contracts'

    def __str__(self):
        return f"Contract {self.contract_id} for Order {self.order.id}"

    def get_absolute_url(self):
        return reverse('verify_contract', args=[self.order.id])

class IDVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='id_verification')
    id_document = models.FileField(
        upload_to='documents/id_verification/%Y/%m/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'pdf'])],
        help_text='Upload a government-approved ID (JPEG, PNG, or PDF)'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_ids'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'ID Verification'
        verbose_name_plural = 'ID Verifications'

    def __str__(self):
        return f"ID Verification for {self.user.username}"

class VerificationRequest(models.Model):
    VERIFICATION_TYPES = (
        ('govt_id', 'Government ID'),
        ('selfie', 'Selfie')
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected')
    )
    
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='verification_requests')
    type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # File fields for storing uploaded documents
    id_document = models.ImageField(
        upload_to='verifications/govt_id/',
        null=True,
        blank=True
    )
    selfie = models.ImageField(
        upload_to='verifications/selfie/',
        null=True,
        blank=True
    )
    
    # New fields for verification status
    acceptance_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')],
        default='pending'
    )
    lender_comment = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} verification for {self.chat_room}"

class PreLendingImage(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='pre_lending_images')
    image = models.ImageField(upload_to='pre_lending_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Pre-lending image for order {self.order.order_id}"

class ProductView(models.Model):
    product = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')  # Prevent duplicate views from same user
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user.username} viewed {self.product.title}"