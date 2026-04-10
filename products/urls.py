from django.urls import path
from . import views

urlpatterns = [
    path('', views.products, name='products'),
    path('products', views.products, name='products-list'),
    path('products/<slug:slug>/', views.product, name='product'),
]
