from decimal import Decimal
from uuid import UUID

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings

from .models import Product
from .policy_content import POLICY_PAGES
from .utils import paginateProducts, searchProducts


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
        price = product.price or Decimal('0')
        subtotal = price * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal,
        })

    subtotal = sum((item['subtotal'] for item in cart_items), Decimal('0'))
    shipping = Decimal('0') if subtotal >= Decimal('500') else Decimal('75')
    total = subtotal + shipping

    return {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping if cart_items else Decimal('0'),
        'total': total if cart_items else Decimal('0'),
        'cart_item_count': sum(item['quantity'] for item in cart_items),
    }


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

    context = _build_cart_context(request)
    return render(request, 'products/cart.html', context)


def checkout(request):
    if not request.session.get('age_verified'):
        return redirect('home')

    cart_context = _build_cart_context(request)
    total = cart_context['total']

    context = {
        'total': total,
        'cart_item_count': cart_context['cart_item_count'],
        'stripe_public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
        'payment_intent_client_secret': '',
    }
    return render(request, 'products/checkout.html', context)


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
