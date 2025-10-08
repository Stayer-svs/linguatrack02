# config/urls.py

from django.contrib import admin
from django.urls import path, include  # Импортируем функцию include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', RedirectView.as_view(url='/my-words/', permanent=True)),
    # Маршруты для админ-панели
    path('admin/', admin.site.urls),

    # Подключаем все маршруты из приложения app_vocab.
    # Теперь все URL-ы из app_vocab/urls.py будут доступны по корню сайта (/).
    path('', include('app_vocab.urls')),
    # АУТЕНТИФИКАЦИЯ
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/register/', include('app_vocab.urls')),  # Наша кастомная регистрация
    path('admin/', admin.site.urls),
    path('', include('app_vocab.urls')),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

