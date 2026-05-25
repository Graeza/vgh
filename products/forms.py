from django import forms

from .models import Product
from users.models import Address


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


class CheckoutShippingDetailsForm(forms.Form):
    full_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'input'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'input'}))
    phone = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'input'}))
    label = forms.CharField(max_length=100, required=False, initial='Home', widget=forms.TextInput(attrs={'class': 'input'}))
    line_1 = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'input'}))
    line_2 = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'input'}))
    city = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'class': 'input'}))
    state = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'class': 'input'}))
    postal_code = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'input'}))
    country = forms.CharField(max_length=100, initial='US', widget=forms.TextInput(attrs={'class': 'input'}))

    def save(self, profile):
        default_address = profile.addresses.filter(is_default=True).first() or profile.addresses.first()
        profile.full_name = self.cleaned_data['full_name']
        profile.email = self.cleaned_data['email']
        profile.save(update_fields=['full_name', 'email'])

        if default_address:
            default_address.phone = self.cleaned_data['phone']
            default_address.save(update_fields=['phone'])
            return default_address

        return Address.objects.create(
            user=profile,
            label=self.cleaned_data['label'] or 'Home',
            recipient_name=self.cleaned_data['full_name'],
            line_1=self.cleaned_data['line_1'],
            line_2=self.cleaned_data['line_2'],
            city=self.cleaned_data['city'],
            state=self.cleaned_data['state'],
            postal_code=self.cleaned_data['postal_code'],
            country=self.cleaned_data['country'],
            phone=self.cleaned_data['phone'],
            is_default=True,
        )
