from django.db import models
from django.contrib.auth.models import User
import uuid


# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(max_length=500, null=True, blank=True)
    username = models.CharField(max_length=200, null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    short_intro = models.CharField(max_length=200, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    profile_image = models.ImageField(null=True, blank=True, upload_to='profiles/', default='profiles/user-default.png')
    social_twitter = models.CharField(max_length=200, null=True, blank=True)
    social_linkedin = models.CharField(max_length=200, null=True, blank=True)
    social_youtube = models.CharField(max_length=200, null=True, blank=True)
    social_instagram = models.CharField(max_length=200, null=True, blank=True)
    points_balance = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return str(self.username)

    class Meta:
        ordering = ['created']

    @property
    def imageURL(self):
        try:
            url = self.profile_image.url
        except Exception:
            url = ''
        return url


class Skill(models.Model):
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return str(self.name)


class Message(models.Model):
    sender = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    recipient = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(max_length=200, null=True, blank=True)
    subject = models.CharField(max_length=200, null=True, blank=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False, null=True)
    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return self.subject

    class Meta:
        ordering = ['is_read', '-created']


class Address(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=100, default='Home')
    recipient_name = models.CharField(max_length=200)
    line_1 = models.CharField(max_length=255)
    line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='US')
    phone = models.CharField(max_length=30, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    class Meta:
        ordering = ['-is_default', '-created']

    def __str__(self):
        return f'{self.recipient_name} - {self.label}'


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='orders')
    shipping_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='orders')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_number = models.CharField(max_length=32, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    placed_at = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    class Meta:
        ordering = ['-placed_at']

    def __str__(self):
        return f'Order {self.id} - {self.user}'


class PointLedger(models.Model):
    EVENT_CHOICES = (
        ('earned', 'Earned'),
        ('redeemed', 'Redeemed'),
        ('adjusted', 'Adjusted'),
        ('purchased', 'Purchased'),
    )

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='point_entries')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='point_entries')
    points = models.IntegerField()
    event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    note = models.CharField(max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'{self.user} {self.event} {self.points}'
