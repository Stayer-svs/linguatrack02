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
    path('register/', views.register, name='register'),
    path('statistics/', views.statistics, name='statistics'),
    path('test/multiple-choice/', views.multiple_choice_test, name='multiple_choice_test'),
    path('test/check-answer/', views.check_multiple_choice, name='check-answer'),
    path('my-words/', views.my_words, name='my_words'),
    path('my-words/add/', views.add_word, name='add_word'),
    path('my-words/remove/<int:word_id>/', views.remove_word, name='remove_word'),
    path('test/matching/', views.matching_game, name='matching_game'),
    path('test/check-matching/', views.check_matching, name='check_matching'),
    path('settings/', views.settings_page, name='settings'),
    path('my-words/review-now/<int:word_id>/', views.review_now, name='review_now'),
    path('export-words/', views.export_words_csv, name='export_words'),
    path('import-words/', views.import_words_csv, name='import_words'),
]