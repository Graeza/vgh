from uuid import UUID

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings

from .models import Product
from .utils import paginateProducts, searchProducts


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

    context = {'age_denied': age_denied}
    return render(request, 'home.html', context)


def products(request):
    if not request.session.get('age_verified'):
        return redirect('home')

    products, search_query = searchProducts(request)
    custom_range, products = paginateProducts(request, products, 6)
    context = {'products': products, 'search_query': search_query, 'custom_range': custom_range}
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

    context = {'product': product}
    return render(request, 'products/product.html', context)


def cart(request):
    if not request.session.get('age_verified'):
        return redirect('home')

    cart_items = []
    for product in Product.objects.filter(is_active=True)[:3]:
        quantity = 1
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': float(product.price or 0) * quantity,
        })

    subtotal = sum(item['subtotal'] for item in cart_items)
    shipping = 0 if subtotal >= 500 else 75
    total = subtotal + shipping

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'products/cart.html', context)


def checkout(request):
    if not request.session.get('age_verified'):
        return redirect('home')

    cart_products = Product.objects.filter(is_active=True)[:3]
    subtotal = sum(float(product.price or 0) for product in cart_products)
    shipping = 0 if subtotal >= 500 else 75
    total = subtotal + shipping

    context = {
        'total': total,
        'stripe_public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
        'payment_intent_client_secret': '',
    }
    return render(request, 'products/checkout.html', context)
