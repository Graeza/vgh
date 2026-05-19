from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db.models import Sum

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

    addresses = profile.addresses.all()
    orders = profile.orders.select_related('product', 'shipping_address')
    point_entries = profile.point_entries.select_related('order')
    point_balance = point_entries.aggregate(total=Sum('points')).get('total') or 0

    context = {
        'addresses': addresses,
        'orders': orders,
        'point_entries': point_entries,
        'point_balance': point_balance,
    }
    return render(request, "users/account.html", context)
