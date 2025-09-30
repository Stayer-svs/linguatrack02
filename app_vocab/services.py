# app_vocab/services.py

from django.utils import timezone
from django.contrib.auth.models import User
from .models import Word, UserWord, UserProfile
import random


def get_or_create_user_profile(user):
    """
    Получает или создает профиль пользователя.
    """
    profile, created = UserProfile.objects.get_or_create(user=user)
    return profile


def get_or_create_user_word(user, word):
    """
    Получает или создает запись прогресса пользователя для слова.
    """
    user_word, created = UserWord.objects.get_or_create(
        user=user,
        word=word,
        defaults={
            'next_review': timezone.now()
        }
    )
    return user_word


def get_today_words(user, limit=20):
    """
    Возвращает слова для повторения сегодня.
    """
    today = timezone.now()

    # Слова, у которых next_review сегодня или раньше
    user_words = UserWord.objects.filter(
        user=user,
        next_review__lte=today
    ).select_related('word')

    # Если слов для повторения мало, добавляем новые
    if user_words.count() < limit:
        # Ищем слова, которые пользователь еще не добавлял
        user_word_ids = UserWord.objects.filter(user=user).values_list('word_id', flat=True)
        new_words = Word.objects.exclude(id__in=user_word_ids)

        # Добавляем случайные новые слова
        new_words_count = min(new_words.count(), limit - user_words.count())
        if new_words_count > 0:
            selected_new_words = random.sample(list(new_words), new_words_count)
            for word in selected_new_words:
                user_word = get_or_create_user_word(user, word)
                user_words = list(user_words) + [user_word]

    return user_words[:limit]


def process_user_answer(user_word, quality):
    """
    Обрабатывает ответ пользователя и обновляет прогресс по алгоритму SM-2.
    quality: 0-5 (0 - полное незнание, 5 - легкое вспоминание)
    """
    # Обновляем прогресс через метод модели
    user_word.update_progress(quality)

    # Обновляем статистику профиля
    profile = get_or_create_user_profile(user_word.user)
    profile.total_reviews += 1

    # Если слово перешло в категорию "изученных"
    if user_word.repetition >= 4:
        profile.total_words_learned = UserWord.objects.filter(
            user=user_word.user,
            repetition__gte=4
        ).count()

    profile.save()

    return user_word


def get_user_statistics(user):
    """
    Возвращает статистику пользователя.
    """
    profile = get_or_create_user_profile(user)
    user_words = UserWord.objects.filter(user=user)

    total_words = user_words.count()
    new_words = user_words.filter(repetition=0).count()
    learning_words = user_words.filter(repetition__range=[1, 3]).count()
    learned_words = user_words.filter(repetition__gte=4).count()

    today_words = get_today_words(user).count()

    return {
        'total_words': total_words,
        'new_words': new_words,
        'learning_words': learning_words,
        'learned_words': learned_words,
        'today_words': today_words,
        'total_reviews': profile.total_reviews,
        'streak_days': profile.streak_days,
    }