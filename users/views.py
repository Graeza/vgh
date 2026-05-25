import os
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template, render_to_string
from .forms import AccountDetailsForm
from .models import PointLedger, Profile
from xhtml2pdf import pisa


def _build_invoice_pdf_response(order, filename):
    static_path = settings.STATIC_ROOT

    def link_callback(uri, rel):
        if uri.startswith(settings.STATIC_URL):
            return os.path.join(static_path, uri.replace(settings.STATIC_URL, ''))
        return os.path.join(static_path, uri)

    template = get_template('products/invoice_pdf.html')
    html = template.render({
        'order': order,
        'logo_path': os.path.join(static_path, 'images', 'vgh_logo.svg'),
        'font_path': os.path.join(static_path, 'fonts'),
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'

    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
        link_callback=link_callback,
        encoding='UTF-8',
    )

    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)

    return response



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
    paid_orders = profile.orders.filter(status='paid').select_related('product')
    orders_by_invoice = {}
    for order in paid_orders:
        if not order.invoice_number:
            continue
        if order.invoice_number not in orders_by_invoice:
            orders_by_invoice[order.invoice_number] = {
                'invoice_number': order.invoice_number,
                'placed_at': order.placed_at,
                'points_redeemed': 0,
            }
        orders_by_invoice[order.invoice_number]['points_redeemed'] += int(order.quantity * order.unit_price)
    orders = sorted(orders_by_invoice.values(), key=lambda entry: entry['placed_at'], reverse=True)
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
def invoice_download(request, invoice_number):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            'username': request.user.username,
            'email': request.user.email,
            'full_name': request.user.get_full_name(),
        },
    )
    invoice_orders = list(
        profile.orders.filter(status='paid', invoice_number=invoice_number).select_related('product')
    )
    if not invoice_orders:
        messages.error(request, 'No invoice is available to download.')
        return redirect('account')

    invoice_snapshot = {
        'invoice_number': invoice_number,
        'created': invoice_orders[0].placed_at,
        'user': {
            'username': profile.username or request.user.username,
            'email': profile.email or request.user.email,
        },
        'items': [
            {
                'product_title': order.product.title,
                'quantity': order.quantity,
                'line_total': order.quantity * order.unit_price,
            }
            for order in invoice_orders
        ],
        'total': sum(order.quantity * order.unit_price for order in invoice_orders),
    }

    return _build_invoice_pdf_response(invoice_snapshot, invoice_number)


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

    points_added = _credit_points_for_session(session)
    if request.user.is_authenticated:
        if points_added > 0:
            messages.success(request, f'Payment successful. {points_added} points were added to your balance.')
        else:
            messages.info(request, 'Payment was already processed for this session.')

    return redirect('account')


def _get_session_metadata(session):
    metadata = getattr(session, 'metadata', None) or {}
    if isinstance(metadata, dict):
        return metadata

    to_dict = getattr(metadata, 'to_dict', None)
    if callable(to_dict):
        return to_dict()

    return dict(metadata)


def _credit_points_for_session(session):
    metadata = _get_session_metadata(session)
    points = int(metadata.get('points', '0'))
    user_id = metadata.get('user_id')
    session_note = f'Stripe session: {session.id}'
    if points < 1 or not user_id:
        return 0

    try:
        user = User.objects.get(id=int(user_id))
    except (User.DoesNotExist, TypeError, ValueError):
        return 0

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name(),
        },
    )

    already_logged = profile.point_entries.filter(note=session_note, event='purchased').exists()
    if already_logged:
        return 0

    profile.points_balance += points
    profile.save(update_fields=['points_balance'])
    PointLedger.objects.create(
        user=profile,
        points=points,
        event='purchased',
        note=session_note,
    )
    return points


@csrf_exempt
def stripe_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=400)

    try:
        import stripe
    except ImportError:
        return HttpResponse(status=500)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event.get('type') == 'checkout.session.completed':
        session = event['data']['object']
        if session.get('payment_status') == 'paid':
            class SessionObject:
                id = session.get('id')
                metadata = session.get('metadata') or {}

            _credit_points_for_session(SessionObject())

    return HttpResponse(status=200)


@login_required
def edit_account_details(request):
    form = AccountDetailsForm(request.POST or None, instance=request.user)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        if form.cleaned_data.get('password'):
            update_session_auth_hash(request, user)
        return redirect('account')

    return render(request, 'users/edit_account_details.html', {'form': form})
