from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render


# Create your views here.
def login_user(request):
    if request.user.is_authenticated:
        return redirect('products-list')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('products-list')

    context = {'form': form}
    return render(request, 'users/login.html', context)


def logout_user(request):
    logout(request)
    return redirect('products-list')
