from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('inbox/', views.inbox, name='inbox'),
    path('account/', views.account, name='account'),
    path('account/edit/', views.edit_account_details, name='edit-account-details'),
]
