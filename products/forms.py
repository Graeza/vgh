from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'title',
            'sku',
            'category',
            'description',
            'stock_quantity',
            'price',
            'thc_min',
            'thc_max',
            'cbd_min',
            'cbd_max',
            'is_lab_tested',
            'is_active',
            'featured_image',
        ]
