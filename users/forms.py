from django import forms
from django.contrib.auth import get_user_model


class AccountDetailsForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        help_text="Leave blank to keep your current password.",
    )

    class Meta:
        model = get_user_model()
        fields = ["username", "email"]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
