from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .forms import AccountDetailsForm
from .models import PointLedger, Profile


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
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, "users/account.html", context)


@login_required
def create_points_checkout_session(request):
    if request.method != 'POST':
        return redirect('account')

    try:
        import stripe
    except ImportError:
        messages.error(request, 'Stripe package is not installed on the server.')
        return redirect('account')

    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, 'Stripe is not configured yet. Please contact support.')
        return redirect('account')

    try:
        points = int(request.POST.get('points', '0'))
    except ValueError:
        points = 0

    if points < 1:
        messages.error(request, 'Please choose at least 1 point.')
        return redirect('account')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode='payment',
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'zar',
                'unit_amount': points * 100,
                'product_data': {'name': f'{points} Gold Points'},
            },
            'quantity': 1,
        }],
        success_url=request.build_absolute_uri(
            reverse('points-purchase-success')
        ) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri(reverse('account')),
        metadata={
            'points': str(points),
            'user_id': str(request.user.id),
        },
    )
    return redirect(session.url, code=303)


@login_required
def points_purchase_success(request):
    session_id = request.GET.get('session_id')
    if not session_id or not settings.STRIPE_SECRET_KEY:
        return redirect('account')

    try:
        import stripe
    except ImportError:
        messages.error(request, 'Stripe package is not installed on the server.')
        return redirect('account')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != 'paid':
        messages.error(request, 'Payment is not completed yet.')
        return redirect('account')

    profile, _ = Profile.objects.get_or_create(user=request.user)
    points = int(session.metadata.get('points', '0'))
    session_note = f'Stripe session: {session_id}'
    already_logged = profile.point_entries.filter(note=session_note, event='purchased').exists()

    if points > 0 and not already_logged:
        profile.points_balance += points
        profile.save(update_fields=['points_balance'])
        PointLedger.objects.create(
            user=profile,
            points=points,
            event='purchased',
            note=session_note,
        )
        messages.success(request, f'Payment successful. {points} points were added to your balance.')

    return redirect('account')


@login_required
def edit_account_details(request):
    form = AccountDetailsForm(request.POST or None, instance=request.user)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        if form.cleaned_data.get('password'):
            update_session_auth_hash(request, user)
        return redirect('account')

    return render(request, 'users/edit_account_details.html', {'form': form})
