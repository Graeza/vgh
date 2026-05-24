from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_user, name='login'),
    path('signup/', views.signup_user, name='signup'),
    path('logout/', views.logout_user, name='logout'),
    path('inbox/', views.inbox, name='inbox'),
    path('account/', views.account, name='account'),
    path('account/edit/', views.edit_account_details, name='edit-account-details'),
    path('account/points/checkout/', views.create_points_checkout_session, name='create-points-checkout-session'),
    path('account/points/success/', views.points_purchase_success, name='points-purchase-success'),
]
