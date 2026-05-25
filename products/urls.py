from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.products, name='products-list'),
    path('products/add/', views.add_product, name='add-product'),
    path('products/<uuid:product_id>/edit/', views.edit_product, name='edit-product'),
    path('products/<uuid:product_id>/delete/', views.delete_product, name='delete-product'),
    path('products/<slug:slug>/', views.product, name='product'),
    path('gallery/', views.gallery, name='gallery'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<uuid:product_id>/', views.add_to_cart, name='add-to-cart'),
    path('cart/update/<uuid:product_id>/', views.update_cart_item, name='update-cart-item'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/', views.checkout_success, name='checkout-success'),
    path('checkout/invoice/', views.invoice_pdf, name='invoice_pdf'),
    path('policy/<slug:slug>/', views.policy_page, name='policy-page'),
]
