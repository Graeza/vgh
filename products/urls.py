from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.products, name='products-list'),
    path('products/<slug:slug>/', views.product, name='product'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<uuid:product_id>/', views.add_to_cart, name='add-to-cart'),
    path('cart/update/<uuid:product_id>/', views.update_cart_item, name='update-cart-item'),
    path('checkout/', views.checkout, name='checkout'),
    path('policy/<slug:slug>/', views.policy_page, name='policy-page'),
]
