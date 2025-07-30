from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import render, redirect
from django.contrib import messages

@login_required
def set_password_after_social(request):
    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hasło zostało ustawione!')
            return redirect('lista_pracownikow')
    else:
        form = SetPasswordForm(request.user)
    return render(request, 'registration/set_password_after_social.html', {'form': form, 'user': request.user})
