"""
URL configuration for baza_pracownikow project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from rest_framework import routers
from django.contrib import admin
from django.urls import  include, path
from django.shortcuts import render
from django.contrib.auth import logout
from pracownicy import views
from django.conf import settings
from django.conf.urls.static import static


def logged_out_view(request):
    return render(request, 'registration/logged_out.html')

def custom_logout_view(request):
    logout(request)
    return render(request, 'registration/logged_out.html')

router = routers.DefaultRouter()
router.register(r'api/pracownicy', views.PracownikViewSet)
router.register(r'api/zespoly', views.ZespolViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/logout/', custom_logout_view, name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/logged_out/', logged_out_view, name='logged_out'),
    path('api/', include(router.urls)),
    path('', include('pracownicy.urls')),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('allauth.socialaccount.urls')),  # social login
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
