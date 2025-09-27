# app_vocab/admin.py

from django.contrib import admin
from .models import Word  # Импортируем нашу модель Word из текущей папки (app_vocab)


# Регистрируем модель Word для отображения в админке
@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    """
    Настройки для отображения модели Word в админ-панели.
    """
    # Поля, которые будут отображаться в списке слов
    list_display = ('original', 'transcription', 'translation', 'knowledge_level', 'date_added')

    # Поле, по которому можно будет искать слова в админке
    search_fields = ('original', 'translation')

    # Фильтры справа для удобной сортировки
    list_filter = ('knowledge_level', 'date_added')

    # Поля, которые будут отображаться и редактироваться на странице редактирования слова
    fields = ('original', 'transcription','translation', 'knowledge_level', 'next_review')