import uuid
from django.db import models
from django.db import models
from django.utils.text import slugify
from users.models import Profile

# Create your models here.

class Product(models.Model):
    CATEGORY_CHOICES = (
        ('flower', 'Flower'),
        ('pre_roll', 'Pre-roll'),
        ('edible', 'Edible'),
        ('vape', 'Vape'),
        ('concentrate', 'Concentrate'),
        ('tincture', 'Tincture'),
        ('topical', 'Topical'),
        ('accessory', 'Accessory'),
    )
        
    owner = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    sku = models.CharField(max_length=64, unique=True, null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='flower')
    description = models.TextField(null=True, blank=True)
    hire = models.BooleanField(default=False, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    thc_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    thc_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    cbd_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    cbd_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_lab_tested = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    featured_image = models.ImageField(null=True, blank=True, default='default.jpg')
    vote_total = models.IntegerField(default=0, null=True, blank=True)
    vote_ratio = models.IntegerField(default=0, null=True, blank=True)
    tags = models.ManyToManyField('Tag',blank=True)
    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self) -> str:
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            base_slug = slugify(self.title)
            slug = base_slug
            count = 1
            while Product.objects.filter(slug=slug).exclude(id=self.id).exists():
                count += 1
                slug = f'{base_slug}-{count}'
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def imageURL(self):
        try:
            return self.featured_image.url
        except ValueError:
            return ''

    class Meta:
        ordering = ['title']
    
class Review(models.Model):
    VOTE_TYPE = (
        ('up','Up Vote'),
        ('down','Down Vote'),
    )
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    body = models.TextField(null=True, blank=True)
    value = models.CharField(max_length=200, choices=VOTE_TYPE)
    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self) -> str:
        return self.value
    
class Tag(models.Model):

    name = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self) -> str:
        return self.name
