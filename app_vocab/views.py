# app_vocab/views.py

import csv
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from django.utils import timezone
from django.http import JsonResponse
from .models import Word, UserWord
from .services import get_today_words, process_user_answer, get_user_statistics, get_or_create_user_profile


@login_required
def word_list(request):
    """
    Главная страница-тренажер с системой интервальных повторений.
    """
    # ФИЛЬТРУЕМ СЛОВА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
    words_for_review = Word.objects.filter(
        userword__user=request.user,  # ДОБАВИТЬ ЭТОТ ФИЛЬТР
        userword__next_review__lte=timezone.now()
    ).order_by('userword__next_review')[:10]

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
            'no_words_message': "У вас пока нет слов для изучения. Добавьте слова в свой словарь!",
            'statistics': get_user_statistics(request.user)
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

###
@login_required
def multiple_choice_test(request):
    """
    Тест с множественным выбором с учетом настроек пользователя.
    """
    from .services import get_today_words
    import random

    profile = get_or_create_user_profile(request.user)

    # Проверяем, включен ли этот тип теста
    if not profile.enable_multiple_choice:
        messages.info(request, "Тест с выбором ответа отключен в настройках.")
        return redirect('app_vocab:settings')

    # Получаем слова с учетом настроек

    from .services import get_words_for_games
    today_words = get_words_for_games(request.user, min_words=5)

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
###
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
    Страница "Мой Словарь" - просмотр всех слов пользователя с сортировкой.
    """
    # Получаем параметр сортировки из GET запроса
    sort_by = request.GET.get('sort', 'date_added')  # по умолчанию по дате добавления

    # ФИЛЬТРУЕМ СЛОВА ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ - ИСПРАВЛЕННАЯ СТРОКА
    user_words = UserWord.objects.filter(user=request.user).select_related('word')

    # Применяем сортировку
    if sort_by == 'original':
        user_words = user_words.order_by('word__original')
    elif sort_by == 'translation':
        user_words = user_words.order_by('word__translation')
    elif sort_by == 'level':
        user_words = user_words.order_by('repetition')
    elif sort_by == 'next_review':
        user_words = user_words.order_by('next_review')
    else:  # date_added (по умолчанию)
        user_words = user_words.order_by('-date_added')

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
        'current_sort': sort_by,
    }
    return render(request, 'app_vocab/my_words.html', context)


@login_required
def add_word(request):
    """Добавление нового слова пользователя"""
    if request.method == 'POST':
        original = request.POST.get('original', '').strip()
        translation = request.POST.get('translation', '').strip()
        transcription = request.POST.get('transcription', '').strip()
        example_sentence = request.POST.get('example_sentence', '').strip()

        if original and translation:
            # ПРОВЕРЯЕМ, не существует ли уже такое слово у пользователя
            existing_word = Word.objects.filter(
                original=original,
                userword__user=request.user  # ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ
            ).first()

            if existing_word:
                messages.error(request, f'Слово "{original}" уже есть в вашем словаре!')
                return redirect('app_vocab:my_words')

            # Создаем новое слово
            word = Word.objects.create(
                original=original,
                translation=translation,
                transcription=transcription,
                example_sentence=example_sentence,
                difficulty_level=0,
            )

            # Создаем связь с пользователем
            UserWord.objects.create(
                user=request.user,
                word=word
            )

            messages.success(request, f'Слово "{original}" успешно добавлено!')
            return redirect('app_vocab:my_words')
        else:
            messages.error(request, 'Заполните обязательные поля: слово и перевод')

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

###
@login_required
def matching_game(request):
    """
    Режим сопоставления с отдельной логикой подбора слов.
    """
    from .services import get_words_for_games
    import random

    profile = get_or_create_user_profile(request.user)

    # Проверяем, включен ли этот тип теста
    if not profile.enable_matching:
        messages.info(request, "Игра в сопоставление отключена в настройках.")
        return redirect('app_vocab:settings')

    # Используем отдельную функцию для игр
    game_words = get_words_for_games(request.user, min_words=4)

    if len(game_words) < 4:
        context = {
            'no_words_message': f"Нужно хотя бы 4 слова для игры. В вашем словаре: {len(game_words)} слов. Добавьте больше слов!"
        }
        return render(request, 'app_vocab/matching_game.html', context)

    # Создаем пары слов для игры
    word_pairs = []
    used_words = set()

    for user_word in game_words:
        if user_word.word.id not in used_words and len(word_pairs) < 6:  # Максимум 6 пар
            word_pairs.append({
                'id': user_word.id,
                'original': user_word.word.original,
                'translation': user_word.word.translation,
                'transcription': user_word.word.transcription,
            })
            used_words.add(user_word.word.id)

    # Разделяем на оригиналы и переводы
    originals = [pair['original'] for pair in word_pairs]
    translations = [pair['translation'] for pair in word_pairs]

    # Перемешиваем
    random.shuffle(originals)
    random.shuffle(translations)

    context = {
        'originals': originals,
        'translations': translations,
        'word_pairs': word_pairs,
        'total_pairs': len(word_pairs),
    }

    return render(request, 'app_vocab/matching_game.html', context)
###
@login_required
def check_matching(request):
    """
    Проверка результатов режима сопоставления.
    """
    if request.method == 'POST':
        matches = request.POST.get('matches', '')

        # Обрабатываем совпадения (формат: original1:translation1,original2:translation2)
        correct_matches = 0
        total_matches = 0

        if matches:
            match_list = matches.split(',')
            total_matches = len(match_list)

            # Здесь должна быть логика проверки правильности совпадений
            # Пока просто считаем что все верно для демонстрации
            correct_matches = total_matches

        context = {
            'correct_matches': correct_matches,
            'total_matches': total_matches,
            'success_rate': (correct_matches / total_matches * 100) if total_matches > 0 else 0,
        }

        return render(request, 'app_vocab/matching_result.html', context)

    return redirect('app_vocab:matching_game')


@login_required
def settings_page(request):
    """
    Страница настроек пользователя.
    """
    profile = get_or_create_user_profile(request.user)

    if request.method == 'POST':
        # Обновляем настройки обучения
        profile.daily_new_words = request.POST.get('daily_new_words', 5)
        profile.daily_review_limit = request.POST.get('daily_review_limit', 20)
        profile.default_interval = request.POST.get('default_interval', 1)

        # Обновляем настройки тестов
        profile.enable_multiple_choice = 'enable_multiple_choice' in request.POST
        profile.enable_matching = 'enable_matching' in request.POST
        profile.test_questions_count = request.POST.get('test_questions_count', 10)

        # Обновляем настройки уведомлений
        profile.notification_enabled = 'notification_enabled' in request.POST
        profile.daily_goal_reminder = 'daily_goal_reminder' in request.POST

        profile.save()
        messages.success(request, 'Настройки успешно сохранены!')
        return redirect('app_vocab:settings')

    context = {
        'profile': profile,
    }
    return render(request, 'app_vocab/settings.html', context)


@login_required
def review_now(request, word_id):
    """
    Устанавливает следующее повторение слова на текущее время (AJAX).
    """
    user_word = get_object_or_404(UserWord, id=word_id, user=request.user)

    # Устанавливаем следующее повторение на текущее время
    user_word.next_review = timezone.now()
    user_word.save()

    # Возвращаем JSON ответ вместо редиректа
    return JsonResponse({
        'success': True,
        'message': f'Слово "{user_word.word.original}" будет повторено в ближайшей тренировке!'
    })

#   messages.success(request, f'Слово "{user_word.word.original}" будет повторено в ближайшей тренировке!')
#   return redirect('app_vocab:my_words')

def register(request):
    """
    Регистрация нового пользователя.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Автоматически логиним пользователя после регистрации
            login(request, user)

            # Создаем профиль пользователя
            from .services import get_or_create_user_profile
            get_or_create_user_profile(user)

            messages.success(request, 'Регистрация прошла успешно! Добро пожаловать!')
            return redirect('app_vocab:word_list')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

###
def export_words_csv(request):
    """Экспорт слов пользователя в CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="my_dictionary.csv"'

    writer = csv.writer(response)
    writer.writerow(['Слово', 'Транскрипция', 'Перевод', 'Уровень сложности', 'Дата добавления'])

    # ИСПРАВЛЕННЫЙ ЗАПРОС - через userword
    words = Word.objects.filter(userword__user=request.user)

    for word in words:
        writer.writerow([
            word.original,
            word.transcription or '',
            word.translation,
            word.get_difficulty_level_display(),
            word.date_added.strftime('%Y-%m-%d') if word.date_added else ''
        ])

    return response
###
def import_words_csv(request):
    """Импорт слов из CSV файла"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            imported_count = 0
            duplicate_count = 0

            for row in reader:
                original = row.get('Слово', '').strip()
                translation = row.get('Перевод', '').strip()

                if not original or not translation:
                    continue

                # ПРОВЕРЯЕМ, не существует ли уже такое слово у пользователя
                existing_word = Word.objects.filter(
                    original=original,
                    userword__user=request.user
                ).first()

                if existing_word:
                    duplicate_count += 1
                    continue

                # Создаем новое слово
                word = Word.objects.create(
                    original=original,
                    translation=translation,
                    transcription=row.get('Транскрипция', '').strip(),
                   #example_sentence=row.get('Пример', '').strip(),
                    difficulty_level=0,
                )

                # Создаем связь с пользователем
                UserWord.objects.create(
                    user=request.user,
                    word=word
                )

                imported_count += 1

            if duplicate_count > 0:
                messages.warning(request,
                                 f'Импортировано {imported_count} слов. Пропущено {duplicate_count} дубликатов.')
            else:
                messages.success(request, f'Успешно импортировано {imported_count} слов!')

        except Exception as e:
            messages.error(request, f'Ошибка при импорте: {str(e)}')

        return redirect('app_vocab:my_words')

    return render(request, 'app_vocab/import_csv.html')