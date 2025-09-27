# app_vocab/urls.py

from django.urls import path
from . import views  # Импортируем наши представления (views) из текущего приложения

# app_name помогает Django уникально идентифицировать URL-ы этого приложения
app_name = 'app_vocab'

urlpatterns = [
    # Путь '' (пустая строка) соответствует корню сайта для этого приложения.
    # views.word_list - это функция, которая будет обрабатывать запрос.
    # name='word_list' - это имя маршрута, чтобы можно было ссылаться на него в коде.
    path('', views.word_list, name='word_list'),
]