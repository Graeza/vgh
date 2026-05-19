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
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input'}),
            'sku': forms.TextInput(attrs={'class': 'input'}),
            'category': forms.TextInput(attrs={'class': 'input'}),
            'description': forms.Textarea(attrs={'class': 'input'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'input'}),
            'price': forms.NumberInput(attrs={'class': 'input'}),
            'thc_min': forms.NumberInput(attrs={'class': 'input'}),
            'thc_max': forms.NumberInput(attrs={'class': 'input'}),
            'cbd_min': forms.NumberInput(attrs={'class': 'input'}),
            'cbd_max': forms.NumberInput(attrs={'class': 'input'}),
            'is_lab_tested': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'featured_image': forms.ClearableFileInput(attrs={'class': 'input'}),
        }
