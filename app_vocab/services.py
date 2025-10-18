# app_vocab/services.py

from django.utils import timezone
from .models import Word, UserWord, UserProfile
import random

from django.contrib.auth.models import User


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


def get_today_words(user, limit=None):
    """
    Возвращает слова для повторения сегодня с учетом настроек пользователя.
    """
    today = timezone.now()
    profile = get_or_create_user_profile(user)

    # Используем лимит из настроек, если не указан явно
    if limit is None:
        limit = profile.daily_review_limit

    # Слова, у которых next_review сегодня или раньше
    user_words = UserWord.objects.filter(
        user=user,
        next_review__lte=today
    ).select_related('word')

    # Если слов для повторения мало, добавляем новые (с учетом настроек)
    if user_words.count() < limit and profile.daily_new_words > 0:
        # Ищем слова, которые пользователь еще не добавлял
        user_word_ids = UserWord.objects.filter(user=user).values_list('word_id', flat=True)
        new_words = Word.objects.exclude(id__in=user_word_ids)

        # Добавляем новые слова согласно настройкам
        new_words_count = min(new_words.count(), profile.daily_new_words, limit - user_words.count())
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

   # today_words = get_today_words(user).count()
    today_words = len(get_today_words(user))

    return {
        'total_words': total_words,
        'new_words': new_words,
        'learning_words': learning_words,
        'learned_words': learned_words,
        'today_words': today_words,
        'total_reviews': profile.total_reviews,
        'streak_days': profile.streak_days,
    }


def get_words_for_games(user, min_words=6):
    """
    Получает слова для игр (берет слова не только по расписанию).
    """
    # Сначала пытаемся взять слова по расписанию
    today_words = list(get_today_words(user, limit=20))

    print(f"🎮 ДЛЯ ИГР: слов по расписанию: {len(today_words)}, нужно минимум: {min_words}")

    # Если мало слов, добавляем случайные из всех слов пользователя
    if len(today_words) < min_words:
        all_user_words = UserWord.objects.filter(user=user).select_related('word')
        additional_words = list(all_user_words)

        # Перемешиваем и добавляем недостающие слова
        random.shuffle(additional_words)
        for word in additional_words:
            if len(today_words) >= min_words * 2:  # Берем в 2 раза больше для пар
                break
            if word not in today_words:
                today_words.append(word)

    # Убираем дубликаты по ID слова
    seen_ids = set()
    unique_words = []
    for user_word in today_words:
        if user_word.word.id not in seen_ids:
            seen_ids.add(user_word.word.id)
            unique_words.append(user_word)

    print(f"🎮 ДЛЯ ИГР: итого уникальных слов: {len(unique_words)}")

    return unique_words[:12]  # Ограничим для удобства игры


from asgiref.sync import sync_to_async


@sync_to_async
def get_quiz_question_async():
    """Асинхронная версия генерации вопроса для теста"""
    return get_quiz_question()


def get_quiz_question():
    """Генерирует вопрос для теста в боте"""
    from .models import Word
    import random

    # Простая синхронная версия получения случайных слов
    all_words = list(Word.objects.all())
    if len(all_words) < 4:
        return None

    words = random.sample(all_words, 4)

    # Случайно выбираем тип вопроса
    question_type = random.choice(['word_to_translation', 'translation_to_word'])

    if question_type == 'word_to_translation':
        correct_word = random.choice(words)
        question = f"Выберите перевод слова:\n<b>{correct_word.original}</b>"
        correct_answer = correct_word.translation
        options = [word.translation for word in words]
    else:
        correct_word = random.choice(words)
        question = f"Выберите слово для перевода:\n<b>{correct_word.translation}</b>"
        correct_answer = correct_word.original
        options = [word.original for word in words]

    random.shuffle(options)

    return {
        'question': question,
        'correct_answer': correct_answer,
        'options': options,
        'type': question_type
    }


@sync_to_async
def get_review_cards_async():
    """Асинхронная версия получения карточек для повторения"""
    return get_review_cards()


def get_review_cards():
    """Возвращает карточки для повторения"""
    from .models import Word
    import random

    # Получаем все слова из базы
    all_words = list(Word.objects.all())

    if not all_words:
        return []

    # Берем случайные слова для повторения (максимум 10)
    num_cards = min(10, len(all_words))
    selected_words = random.sample(all_words, num_cards)


    # Формируем карточки
    cards = []
    for word in selected_words:
        cards.append({
            'word': word.original,
            'translation': word.translation,
            'id': word.id
        })

    return cards