from decimal import Decimal
from uuid import UUID

from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.contrib import messages
from django.db import transaction

from .models import InvoiceSequence, Product
from .forms import CheckoutShippingDetailsForm, ProductForm
from users.models import Order, PointLedger
from .policy_content import POLICY_PAGES
from .utils import paginateProducts, searchProducts


def _build_simple_invoice_pdf(order):
    def _escape(value):
        text = str(value or '')
        return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    lines = [
        'VGH Invoice',
        f'Invoice Number: {order.get("invoice_number", "")}',
        f'Created: {order.get("created", "")}',
        f'Customer: {order.get("user", {}).get("username", "")}',
        f'Email: {order.get("user", {}).get("email", "")}',
        '',
        'Items:',
    ]
    for item in order.get('items', []):
        lines.append(
            f"- {item.get('product_title', '')} x{item.get('quantity', 0)} = {item.get('line_total', 0)}"
        )
    lines.extend(['', f"Total: {order.get('total', 0)}"])

    text_ops = ['BT', '/F1 12 Tf', '50 780 Td', '14 TL']
    for idx, line in enumerate(lines):
        escaped = _escape(line)
        text_ops.append(f'({escaped}) Tj')
        if idx < len(lines) - 1:
            text_ops.append('T*')
    text_ops.append('ET')
    content = '\n'.join(text_ops).encode('utf-8')

    objects = []
    objects.append(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
    objects.append(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
    objects.append(
        b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n'
    )
    objects.append(b'4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n')
    objects.append(f'5 0 obj\n<< /Length {len(content)} >>\nstream\n'.encode('utf-8') + content + b'\nendstream\nendobj\n')

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f'xref\n0 {len(offsets)}\n'.encode('utf-8'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('utf-8'))
    pdf.extend(
        f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF'.encode('utf-8')
    )
    return bytes(pdf)


def _get_cart_data(request):
    return request.session.get('cart', {})


def _save_cart_data(request, cart_data):
    request.session['cart'] = cart_data
    request.session.modified = True


def _cart_item_count(request):
    total = 0
    for quantity in _get_cart_data(request).values():
        try:
            total += int(quantity)
        except (TypeError, ValueError):
            continue
    return total


from django.utils import timezone


def _build_cart_context(request):
    cart_data = _get_cart_data(request)
    quantities_by_id = {}
    for product_id, quantity in cart_data.items():
        try:
            parsed_quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        if parsed_quantity > 0:
            quantities_by_id[product_id] = parsed_quantity

    products = Product.objects.filter(is_active=True, id__in=quantities_by_id.keys())
    cart_items = []
    for product in products:
        quantity = quantities_by_id.get(str(product.id), 0)
        points_per_item = int((product.price or Decimal('0')).to_integral_value())
        subtotal = points_per_item * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal,
        })

    subtotal = sum((item['subtotal'] for item in cart_items), 0)
    shipping_selected = request.session.get('shipping_selected', False)
    shipping = 125 if cart_items and shipping_selected else 0
    total = subtotal + shipping

    return {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping if cart_items else 0,
        'shipping_selected': shipping_selected if cart_items else False,
        'total': total if cart_items else 0,
        'cart_item_count': sum(item['quantity'] for item in cart_items),
    }


def _build_invoice_snapshot(request, cart_context, profile):
    cart_items = []
    for item in cart_context['cart_items']:
        cart_items.append({
            'product_title': item['product'].title,
            'quantity': item['quantity'],
            'line_total': item['subtotal'],
        })

    with transaction.atomic():
        sequence, _ = InvoiceSequence.objects.select_for_update().get_or_create(
            pk=1,
            defaults={'next_number': 1},
        )
        latest_order_number = sequence.next_number
        sequence.next_number += 1
        sequence.save(update_fields=['next_number'])

    invoice_number = f'INV-{latest_order_number:06d}'
    return {
        'invoice_number': invoice_number,
        'created': timezone.now().isoformat(),
        'total': cart_context['total'],
        'items': cart_items,
        'user': {
            'username': profile.username or profile.user.username,
            'email': profile.email or profile.user.email,
        },
    }


def _create_paid_orders(profile, cart_context, invoice_number):
    default_address = profile.addresses.filter(is_default=True).first() or profile.addresses.first()
    if not default_address:
        return []

    created_orders = []
    for item in cart_context['cart_items']:
        product = item['product']
        created_orders.append(
            Order.objects.create(
                user=profile,
                product=product,
                shipping_address=default_address,
                quantity=item['quantity'],
                unit_price=product.price or Decimal('0'),
                invoice_number=invoice_number,
                status='paid',
            )
        )
    return created_orders


# Create your views here.
def home(request):
    age_denied = False

    if request.method == 'POST':
        is_of_age = request.POST.get('is_of_age')

        if is_of_age == 'yes':
            request.session['age_verified'] = True
            return redirect('products-list')

        request.session['age_verified'] = False
        age_denied = True

    context = {
        'age_denied': age_denied,
        'show_age_gate': not request.session.get('age_verified', False),
    }
    return render(request, 'home.html', context)


def products(request):
    if not request.session.get('age_verified'):
        return redirect('home')

    products, search_query = searchProducts(request)
    custom_range, products = paginateProducts(request, products, 6)
    cart_item_count = _cart_item_count(request)
    context = {
        'products': products,
        'search_query': search_query,
        'custom_range': custom_range,
        'cart_item_count': cart_item_count,
    }
    return render(request, 'products/products.html', context)




@login_required
def add_product(request):
    if not request.user.is_superuser:
        raise Http404('Page not found.')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully.')
            return redirect('products-list')
    else:
        form = ProductForm()

    products = Product.objects.all().order_by('title')

    context = {
        'form': form,
        'products': products,
        'cart_item_count': _cart_item_count(request),
    }
    return render(request, 'products/add_product.html', context)


@login_required
def edit_product(request, product_id):
    if not request.user.is_superuser:
        raise Http404('Page not found.')

    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('add-product')
    else:
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'products': Product.objects.all().order_by('title'),
        'editing_product': product,
        'cart_item_count': _cart_item_count(request),
    }
    return render(request, 'products/add_product.html', context)


@login_required
def delete_product(request, product_id):
    if not request.user.is_superuser:
        raise Http404('Page not found.')
    if request.method != 'POST':
        return redirect('add-product')

    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully.')
    return redirect('add-product')


def product(request, slug):
    if not request.session.get('age_verified'):
        return redirect('home')

    active_products = Product.objects.filter(is_active=True)
    product = active_products.filter(slug=slug).first()

    if product is None:
        try:
            product_uuid = UUID(str(slug))
        except ValueError:
            raise Http404('No Product matches the given query.')

        product = get_object_or_404(active_products, id=product_uuid)

    cart_item_count = _cart_item_count(request)
    context = {'product': product, 'cart_item_count': cart_item_count}
    return render(request, 'products/product.html', context)


def cart(request):
    if not request.session.get('age_verified'):
        return redirect('home')

    if request.method == 'POST':
        request.session['shipping_selected'] = request.POST.get('shipping_selected') == 'on'
        request.session.modified = True
        return redirect('cart')

    context = _build_cart_context(request)
    return render(request, 'products/cart.html', context)


def checkout(request):
    if not request.session.get('age_verified'):
        return redirect('home')

    cart_context = _build_cart_context(request)
    total = cart_context['total']

    if not request.user.is_authenticated:
        messages.error(request, 'Please sign in to redeem points at checkout.')
        return redirect('login')

    profile = request.user.profile
    default_address = profile.addresses.filter(is_default=True).first() or profile.addresses.first()
    has_contact_details = bool(profile.full_name and profile.email)
    has_shipping_details = bool(default_address and default_address.phone)
    needs_shipping_details_form = cart_context['shipping_selected'] and (
        not default_address or not has_contact_details or not has_shipping_details
    )

    if needs_shipping_details_form:
        initial_details = {
            'full_name': profile.full_name or request.user.get_full_name() or request.user.username,
            'email': profile.email or request.user.email,
            'phone': default_address.phone if default_address else '',
            'label': default_address.label if default_address else 'Home',
            'line_1': default_address.line_1 if default_address else '',
            'line_2': default_address.line_2 if default_address else '',
            'city': default_address.city if default_address else '',
            'state': default_address.state if default_address else '',
            'postal_code': default_address.postal_code if default_address else '',
            'country': default_address.country if default_address else 'US',
        }
    else:
        initial_details = {}

    shipping_details_form = CheckoutShippingDetailsForm(initial=initial_details)

    if request.method == 'POST':
        if request.POST.get('action') == 'save-shipping-details':
            shipping_details_form = CheckoutShippingDetailsForm(request.POST)
            if shipping_details_form.is_valid():
                shipping_details_form.save(profile)
                messages.success(request, 'Shipping and contact details saved.')
                return redirect('checkout')
            messages.error(request, 'Please correct the shipping details below.')
            context = {
                'cart_items': cart_context['cart_items'],
                'subtotal': cart_context['subtotal'],
                'shipping': cart_context['shipping'],
                'shipping_selected': cart_context['shipping_selected'],
                'total': total,
                'cart_item_count': cart_context['cart_item_count'],
                'available_points': profile.points_balance,
                'needed_points': max(total - profile.points_balance, 0),
                'shipping_details_form': shipping_details_form,
                'needs_shipping_details_form': True,
            }
            return render(request, 'products/checkout.html', context)

        if not cart_context['cart_items']:
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')

        if cart_context['shipping_selected']:
            default_address = profile.addresses.filter(is_default=True).first() or profile.addresses.first()
            has_contact_details = bool(profile.full_name and profile.email)
            has_shipping_details = bool(default_address and default_address.phone)
            if not default_address or not has_contact_details or not has_shipping_details:
                messages.error(request, 'Please save your shipping and contact details before checkout.')
                return redirect('checkout')

        if profile.points_balance < total:
            messages.error(request, 'You do not have enough points for this order.')
            return redirect('checkout')

        profile.points_balance -= total
        profile.save(update_fields=['points_balance'])
        PointLedger.objects.create(
            user=profile,
            points=-total,
            event='redeemed',
            note='Redeemed points at checkout',
        )
        invoice_snapshot = _build_invoice_snapshot(request, cart_context, profile)
        _create_paid_orders(profile, cart_context, invoice_snapshot['invoice_number'])
        request.session['latest_invoice'] = invoice_snapshot
        _save_cart_data(request, {})
        messages.success(request, f'Checkout complete. {total} points redeemed.')
        return redirect('checkout-success')

    context = {
        'cart_items': cart_context['cart_items'],
        'subtotal': cart_context['subtotal'],
        'shipping': cart_context['shipping'],
        'shipping_selected': cart_context['shipping_selected'],
        'total': total,
        'cart_item_count': cart_context['cart_item_count'],
        'available_points': profile.points_balance,
        'needed_points': max(total - profile.points_balance, 0),
        'shipping_details_form': shipping_details_form,
        'needs_shipping_details_form': needs_shipping_details_form,
    }
    return render(request, 'products/checkout.html', context)


@login_required
def checkout_success(request):
    invoice = request.session.get('latest_invoice')
    if not invoice:
        messages.error(request, 'No completed purchase was found.')
        return redirect('products-list')

    context = {
        'order': invoice,
        'cart_item_count': _cart_item_count(request),
    }
    return render(request, 'products/success.html', context)


@login_required
def invoice_pdf(request):
    invoice = request.session.get('latest_invoice')
    if not invoice:
        messages.error(request, 'No invoice is available to download.')
        return redirect('products-list')

    pdf_bytes = _build_simple_invoice_pdf(invoice)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice["invoice_number"]}.pdf"'
    return response




def gallery(request):
    context = {
        'cart_item_count': _cart_item_count(request),
    }
    return render(request, 'products/gallery.html', context)

def policy_page(request, slug):
    page = POLICY_PAGES.get(slug)
    if page is None:
        raise Http404('Policy page not found.')

    context = {
        'page': page,
        'cart_item_count': _cart_item_count(request),
    }
    return render(request, 'products/policy_page.html', context)


def add_to_cart(request, product_id):
    if not request.session.get('age_verified'):
        return redirect('home')

    if request.method != 'POST':
        return redirect('products-list')

    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart_data = _get_cart_data(request)
    product_key = str(product.id)
    cart_data[product_key] = cart_data.get(product_key, 0) + 1
    _save_cart_data(request, cart_data)
    return redirect(request.POST.get('next') or 'cart')


def update_cart_item(request, product_id):
    if not request.session.get('age_verified'):
        return redirect('home')

    if request.method != 'POST':
        return redirect('cart')

    product = get_object_or_404(Product, id=product_id, is_active=True)
    action = request.POST.get('action')
    product_key = str(product.id)
    cart_data = _get_cart_data(request)
    current_quantity = int(cart_data.get(product_key, 0))

    if action == 'increase':
        cart_data[product_key] = current_quantity + 1
    elif action == 'decrease':
        next_quantity = current_quantity - 1
        if next_quantity > 0:
            cart_data[product_key] = next_quantity
        else:
            cart_data.pop(product_key, None)
    elif action == 'remove':
        cart_data.pop(product_key, None)

    _save_cart_data(request, cart_data)
    return redirect('cart')
