"""
URL configuration for arkham_nexus project.

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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from accounts.views import CustomLoginView, CustomSignUpView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Custom authentication views
    path('login/', CustomLoginView.as_view(), name='account_login'),
    path('signup/', CustomSignUpView.as_view(), name='account_signup'),
    
    # API URLs
    path('api/accounts/', include('accounts.urls')),
    path('api/schedules/', include('schedules.urls')),
    path('api/scenarios/', include('scenarios.urls')),
    
    # Web URLs  
    path('accounts/', include('accounts.urls')),
    
    # Allauth URLs (excluding login/signup) - moved after custom accounts URLs
    path('auth/', include('allauth.urls')),
    
    # Home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
