from django import forms
from django.contrib.auth.models import User

from .models import Address


class AccountDetailsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "label",
            "recipient_name",
            "line_1",
            "line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
            "is_default",
        ]
