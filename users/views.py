from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AccountDetailsForm, AddressForm
from .models import Address, Profile


# Create your views here.
def login_user(request):
    if request.user.is_authenticated:
        return redirect('products-list')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('products-list')

    context = {'form': form}
    return render(request, 'users/login.html', context)


def logout_user(request):
    logout(request)
    return redirect('products-list')


@login_required
def inbox(request):
    return render(request, "users/inbox.html")


@login_required
def account(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            'username': request.user.username,
            'email': request.user.email,
            'full_name': request.user.get_full_name(),
        },
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update-account':
            account_form = AccountDetailsForm(request.POST, instance=request.user)
            if account_form.is_valid():
                account_form.save()
                profile.username = request.user.username
                profile.email = request.user.email
                profile.full_name = request.user.get_full_name()
                profile.save(update_fields=['username', 'email', 'full_name'])
                messages.success(request, 'Account details updated.')
                return redirect('account')
            messages.error(request, 'Please correct the account form errors.')

        elif action == 'add-address':
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = profile
                if address.is_default:
                    profile.addresses.update(is_default=False)
                address.save()
                messages.success(request, 'Address added.')
                return redirect('account')
            messages.error(request, 'Please correct the new address form errors.')

        elif action == 'update-address':
            address = get_object_or_404(Address, id=request.POST.get('address_id'), user=profile)
            address_form = AddressForm(request.POST, instance=address)
            if address_form.is_valid():
                updated_address = address_form.save(commit=False)
                if updated_address.is_default:
                    profile.addresses.exclude(id=address.id).update(is_default=False)
                updated_address.save()
                messages.success(request, 'Address updated.')
                return redirect('account')
            messages.error(request, 'Please correct the address form errors.')

        elif action == 'delete-address':
            address = get_object_or_404(Address, id=request.POST.get('address_id'), user=profile)
            address.delete()
            messages.success(request, 'Address deleted.')
            return redirect('account')

    addresses = profile.addresses.all()
    orders = profile.orders.select_related('product', 'shipping_address')
    point_entries = profile.point_entries.select_related('order')
    point_balance = profile.points_balance

    context = {
        'addresses': addresses,
        'orders': orders,
        'point_entries': point_entries,
        'point_balance': point_balance,
        'account_form': AccountDetailsForm(instance=request.user),
        'address_form': AddressForm(),
    }
    return render(request, "users/account.html", context)
