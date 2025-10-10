# app_vocab/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


class Word(models.Model):
    """
    Модель для хранения слова (общие данные для всех пользователей).
    """
    original = models.CharField(max_length=100, verbose_name='Иностранное слово')
    transcription = models.CharField(max_length=100, blank=True, verbose_name='Транскрипция')
    translation = models.CharField(max_length=100, verbose_name='Перевод')
    date_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    # Примеры использования (для подсказок в упражнениях)
    example_sentence = models.TextField(blank=True, verbose_name='Пример использования')

    # Уровень сложности слова (общий для всех)
    difficulty_level = models.IntegerField(
        choices=[(1, 'Легкий'), (2, 'Средний'), (3, 'Сложный')],
        default=2,
        verbose_name='Уровень сложности'
    )

    class Meta:
        verbose_name = 'Слово'
        verbose_name_plural = 'Слова'
        ordering = ['-date_added']

    def __str__(self):
        return f"{self.original} - {self.translation}"


class UserWord(models.Model):
    """
    Модель для хранения прогресса КОНКРЕТНОГО пользователя по КОНКРЕТНОМУ слову.
    Реализует алгоритм интервальных повторений SM-2.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, verbose_name='Слово')

    # Параметры алгоритма SM-2
    interval = models.IntegerField(default=0, verbose_name='Интервал (дни)')
    repetition = models.IntegerField(default=0, verbose_name='Номер повторения')
    ease_factor = models.FloatField(default=2.5, verbose_name='Фактор легкости')
    next_review = models.DateTimeField(default=timezone.now, verbose_name='Следующее повторение')

    # Статистика
    correct_answers = models.IntegerField(default=0, verbose_name='Правильных ответов')
    wrong_answers = models.IntegerField(default=0, verbose_name='Неправильных ответов')
    last_reviewed = models.DateTimeField(null=True, blank=True, verbose_name='Последнее повторение')

    date_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления пользователю')

    class Meta:
        verbose_name = 'Прогресс пользователя'
        verbose_name_plural = 'Прогресс пользователей'
        unique_together = ['user', 'word']  # Важно: одна запись на пользователя и слово

    def __str__(self):
        return f"{self.user.username} - {self.word.original} (ур. {self.repetition})"

    def update_progress(self, quality):
        """
        Алгоритм SM-2 для обновления интервалов повторений.
        quality: 0-5 (0 - полное незнание, 5 - легкое вспоминание)
        """
        if quality < 3:
            # Неправильный ответ - начинаем заново
            self.repetition = 0
            self.interval = 0
        else:
            # Правильный ответ
            if self.repetition == 0:
                self.interval = 1
            elif self.repetition == 1:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.ease_factor)

            self.repetition += 1

        # Обновляем фактор легкости
        self.ease_factor = max(1.3, self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

        # Устанавливаем следующее повторение
        self.next_review = timezone.now() + datetime.timedelta(days=self.interval)
        self.last_reviewed = timezone.now()

        # Обновляем статистику
        if quality >= 3:
            self.correct_answers += 1
        else:
            self.wrong_answers += 1

        self.save()

    def get_knowledge_level(self):
        """Возвращает человеко-понятный уровень знания слова"""
        if self.repetition == 0:
            return "Новое"
        elif self.repetition == 1:
            return "Начальный"
        elif self.repetition <= 3:
            return "Повторяемое"
        else:
            return "Изученное"


class UserProfile(models.Model):
    """
    Расширенный профиль пользователя для хранения настроек и статистики.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    telegram_id = models.BigIntegerField(null=True, blank=True, verbose_name='Telegram ID')
    daily_review_limit = models.IntegerField(default=20, verbose_name='Лимит повторений в день')
    notification_enabled = models.BooleanField(default=True, verbose_name='Уведомления включены')

    # Статистика обучения
    total_words_learned = models.IntegerField(default=0, verbose_name='Всего изучено слов')
    total_reviews = models.IntegerField(default=0, verbose_name='Всего повторений')
    streak_days = models.IntegerField(default=0, verbose_name='Дней подряд')

    # НОВЫЕ поля настроек (ДОБАВИТЬ эти строки):
    daily_new_words = models.IntegerField(default=5, verbose_name='Новых слов в день')
    default_interval = models.IntegerField(default=1, verbose_name='Базовый интервал (дни)')

    # Настройки тестов (ДОБАВИТЬ):
    enable_multiple_choice = models.BooleanField(default=True, verbose_name='Тест с выбором')
    enable_matching = models.BooleanField(default=True, verbose_name='Сопоставление')
    test_questions_count = models.IntegerField(default=10, verbose_name='Вопросов в тесте')

    # Уведомления (можно заменить существующее поле или оставить оба):
    daily_goal_reminder = models.BooleanField(default=True, verbose_name='Напоминание о целях')

    # телеграм бот
    telegram_id = models.CharField(max_length=100, blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f"Профиль: {self.user.username}"
