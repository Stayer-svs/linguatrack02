# config/urls.py

from django.contrib import admin
from django.urls import path, include  # Импортируем функцию include

urlpatterns = [
    # Маршруты для админ-панели
    path('admin/', admin.site.urls),

    # Подключаем все маршруты из приложения app_vocab.
    # Теперь все URL-ы из app_vocab/urls.py будут доступны по корню сайта (/).
    path('', include('app_vocab.urls')),
]