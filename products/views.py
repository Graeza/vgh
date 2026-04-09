from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, Tag
# from .forms import ProductForm, ReviewForm
from .utils import searchProducts, paginateProducts


# Create your views here.
def products(request):
    products, search_query = searchProducts(request)
    custom_range, products = paginateProducts(request, products, 6)
    context = {'products': products, 'search_query':search_query, 'custom_range':custom_range}
    return render(request, 'products/products.html', context)