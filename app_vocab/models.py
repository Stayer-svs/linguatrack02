# app_vocab/models.py

from django.db import models


class Word(models.Model):
    """
    Модель для хранения слова и его перевода.
    """
    # Слово на иностранном языке (обязательное поле, макс. длина 100 символов)
    original = models.CharField(max_length=100, verbose_name='Иностранное слово')

    # Транскрипция (НЕобязательное поле, макс. длина 100 символов)
    transcription = models.CharField(max_length=100, blank=True, verbose_name='Транскрипция')  # НОВОЕ ПОЛЕ

    # Перевод на родной язык (обязательное поле, макс. длина 100 символов)
    translation = models.CharField(max_length=100, verbose_name='Перевод')

    # Дата и время добавления слова (автоматически устанавливается при создании)
    date_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    # Уровень знания слова (по умолчанию 0 - новое слово)
    knowledge_level = models.IntegerField(default=0, verbose_name='Уровень знания')

    # Следующее повторение слова (может быть пустым для новых слов)
    next_review = models.DateTimeField(null=True, blank=True, verbose_name='Следующее повторение')

    class Meta:
        verbose_name = 'Слово'
        verbose_name_plural = 'Слова'
        ordering = ['-date_added']

    def __str__(self):
        return f"{self.original} - {self.translation}"