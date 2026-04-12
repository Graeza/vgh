from uuid import UUID

from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Product
from .utils import searchProducts, paginateProducts

# Create your views here.
def products(request):
    products, search_query = searchProducts(request)
    custom_range, products = paginateProducts(request, products, 6)
    context = {'products': products, 'search_query': search_query, 'custom_range': custom_range}
    return render(request, 'products/products.html', context)

def product(request, slug):
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
