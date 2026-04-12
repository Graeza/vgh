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
    product = get_object_or_404(Product, slug=slug, is_active=True)
    context = {'product': product}
    return render(request, 'products/product.html', context)