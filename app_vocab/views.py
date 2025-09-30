# app_vocab/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Word, UserWord
from .services import get_today_words, process_user_answer, get_user_statistics


@login_required
def word_list(request):
    """
    Главная страница-тренажер с системой интервальных повторений.
    """
    # Получаем параметры из URL
    is_reverse = request.GET.get('reverse', '0') == '1'
    word_id = request.GET.get('word_id')
    action = request.GET.get('action')

    # Обрабатываем действия со словами
    if word_id and action:
        user_word = get_object_or_404(UserWord, id=word_id, user=request.user)

        if action == 'show_translation':
            # Просто показываем перевод - не меняем прогресс
            pass
        elif action == 'know':
            # Пользователь знает слово (quality=4 - "знал с задержкой")
            process_user_answer(user_word, quality=4)
        elif action == 'dont_know':
            # Пользователь не знает слово (quality=2 - "почти вспомнил")
            process_user_answer(user_word, quality=2)

        # Перенаправляем обратно на страницу
        redirect_url = f"{request.path}?reverse={int(is_reverse)}"
        return redirect(redirect_url)

    # Получаем слова для повторения сегодня
    today_words = get_today_words(request.user, limit=20)

    # Если слов нет, предлагаем добавить слова
    if not today_words:
        context = {
            'words': [],
            'is_reverse': is_reverse,
            'no_words_message': "У вас пока нет слов для изучения. Добавьте слова через админку!"
        }
        return render(request, 'app_vocab/word_list.html', context)

    # Передаем UserWord объекты в шаблон (а не просто Word)
    context = {
        'user_words': today_words,
        'is_reverse': is_reverse,
        'statistics': get_user_statistics(request.user),
    }
    return render(request, 'app_vocab/word_list.html', context)


@login_required
def statistics(request):
    """
    Страница со статистикой пользователя.
    """
    stats = get_user_statistics(request.user)
    return render(request, 'app_vocab/statistics.html', {'statistics': stats})


# app_vocab/views.py (добавьте в конец файла)

@login_required
def multiple_choice_test(request):
    """
    Тест с множественным выбором - 4 варианта, 1 правильный.
    """
    from .services import get_today_words
    import random

    # Получаем слова для сегодня
    today_words = get_today_words(request.user, limit=10)

    if not today_words:
        context = {
            'no_words_message': "Нет слов для тестирования. Добавьте слова или подождите следующего повторения."
        }
        return render(request, 'app_vocab/multiple_choice.html', context)

    # Выбираем случайное слово для вопроса
    question_word = random.choice(today_words)

    # Создаем варианты ответов
    all_words = list(Word.objects.exclude(id=question_word.word.id))
    wrong_answers = random.sample(all_words, min(3, len(all_words)))

    # Собираем все варианты (правильный + неправильные)
    options = [question_word.word] + wrong_answers
    random.shuffle(options)  # Перемешиваем варианты

    # Определяем правильный ответ
    correct_answer_id = question_word.word.id

    context = {
        'question_word': question_word,
        'options': options,
        'correct_answer_id': correct_answer_id,
        'total_questions': len(today_words),
    }

    return render(request, 'app_vocab/multiple_choice.html', context)


@login_required
def check_multiple_choice(request):
    """
    Проверка ответа в тесте с множественным выбором.
    """
    if request.method == 'POST':
        selected_answer_id = request.POST.get('selected_answer')
        correct_answer_id = request.POST.get('correct_answer')
        question_word_id = request.POST.get('question_word_id')

        # Проверяем ответ
        is_correct = int(selected_answer_id) == int(correct_answer_id)

        # Обновляем прогресс пользователя
        if is_correct and question_word_id:
            try:
                user_word = UserWord.objects.get(
                    id=question_word_id,
                    user=request.user
                )
                process_user_answer(user_word, quality=4)  # "Знал легко"
            except UserWord.DoesNotExist:
                pass

        context = {
            'is_correct': is_correct,
            'selected_answer_id': int(selected_answer_id),
            'correct_answer_id': int(correct_answer_id),
        }

        return render(request, 'app_vocab/test_result.html', context)

    return redirect('app_vocab:multiple_choice_test')


# app_vocab/views.py (добавьте в конец)

@login_required
def my_words(request):
    """
    Страница "Мои слова" - просмотр всех слов пользователя.
    """
    user_words = UserWord.objects.filter(user=request.user).select_related('word')

    # Статистика по словам пользователя
    words_stats = {
        'total': user_words.count(),
        'new': user_words.filter(repetition=0).count(),
        'learning': user_words.filter(repetition__range=[1, 3]).count(),
        'learned': user_words.filter(repetition__gte=4).count(),
    }

    context = {
        'user_words': user_words,
        'words_stats': words_stats,
    }
    return render(request, 'app_vocab/my_words.html', context)


@login_required
def add_word(request):
    """
    Добавление нового слова пользователем.
    """
    if request.method == 'POST':
        original = request.POST.get('original')
        transcription = request.POST.get('transcription', '')
        translation = request.POST.get('translation')

        if original and translation:
            # Создаем или получаем слово
            word, created = Word.objects.get_or_create(
                original=original.strip(),
                defaults={
                    'transcription': transcription.strip(),
                    'translation': translation.strip(),
                }
            )

            # Если слово уже существует, но пользователь хочет свою версию
            if not created:
                # Можно обновить транскрипцию, если она отличается
                if transcription and word.transcription != transcription:
                    word.transcription = transcription
                    word.save()

            # Связываем слово с пользователем
            user_word, user_word_created = UserWord.objects.get_or_create(
                user=request.user,
                word=word
            )

            if user_word_created:
                messages.success(request, f'Слово "{original}" добавлено в ваш словарь!')
            else:
                messages.info(request, f'Слово "{original}" уже есть в вашем словаре.')

            return redirect('app_vocab:my_words')
        else:
            messages.error(request, 'Заполните обязательные поля: слово и перевод.')

    return render(request, 'app_vocab/add_word.html')


@login_required
def remove_word(request, word_id):
    """
    Удаление слова из словаря пользователя.
    """
    try:
        user_word = UserWord.objects.get(id=word_id, user=request.user)
        word_text = user_word.word.original
        user_word.delete()
        messages.success(request, f'Слово "{word_text}" удалено из вашего словаря.')
    except UserWord.DoesNotExist:
        messages.error(request, 'Слово не найдено в вашем словаре.')

    return redirect('app_vocab:my_words')
