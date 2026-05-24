from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .forms import AccountDetailsForm
from .models import Profile


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


def signup_user(request):
    if request.user.is_authenticated:
        return redirect('products-list')

    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('products-list')

    return render(request, 'users/signup.html', {'form': form})


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
        action = request.POST.get('address_action')
        if action == 'remove':
            address = get_object_or_404(profile.addresses, id=request.POST.get('address_id'))
            address.delete()
            return redirect('account')

        if action in {'add', 'edit'}:
            address_id = request.POST.get('address_id')
            if action == 'edit':
                address = get_object_or_404(profile.addresses, id=address_id)
            else:
                address = profile.addresses.model(user=profile)

            address.label = request.POST.get('label', '').strip() or 'Home'
            address.recipient_name = request.POST.get('recipient_name', '').strip()
            address.line_1 = request.POST.get('line_1', '').strip()
            address.line_2 = request.POST.get('line_2', '').strip()
            address.city = request.POST.get('city', '').strip()
            address.state = request.POST.get('state', '').strip()
            address.postal_code = request.POST.get('postal_code', '').strip()
            address.country = request.POST.get('country', '').strip() or 'US'
            address.phone = request.POST.get('phone', '').strip()
            address.is_default = request.POST.get('is_default') == 'on'

            if address.is_default:
                profile.addresses.exclude(id=address.id).update(is_default=False)

            required_values = [
                address.recipient_name,
                address.line_1,
                address.city,
                address.state,
                address.postal_code,
            ]
            if all(required_values):
                address.save()
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
    }
    return render(request, "users/account.html", context)


@login_required
def edit_account_details(request):
    form = AccountDetailsForm(request.POST or None, instance=request.user)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        if form.cleaned_data.get('password'):
            update_session_auth_hash(request, user)
        return redirect('account')

    return render(request, 'users/edit_account_details.html', {'form': form})
