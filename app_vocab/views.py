# app_vocab/views.py

from django.shortcuts import render, get_object_or_404, redirect
from .models import Word

def word_list(request):
    """
    Представление для главной страницы-тренажера.
    Обрабатывает фильтры, реверс и действия со словами.
    """
    # Получаем параметры из URL
    is_reverse = request.GET.get('reverse', '0') == '1'
    filter_type = request.GET.get('filter', 'all')  # 'all', 'new', 'for_review', 'learned'
    word_id = request.GET.get('word_id')
    action = request.GET.get('action')

    # Обрабатываем действия со словами (знаю/не знаю)
    if word_id and action:
        word = get_object_or_404(Word, id=word_id)

        if action == 'show_translation':
            request.session['show_translation'] = True
        elif action == 'know':
            word.knowledge_level += 1
            word.save()
        elif action == 'dont_know':
            if word.knowledge_level > 0:
                word.knowledge_level -= 1
                word.save()
        # После действия перенаправляем, сохраняя текущие фильтр и режим реверса
        redirect_url = f"{request.path}?filter={filter_type}&reverse={int(is_reverse)}"
        return redirect(redirect_url)

    # ФИЛЬТРАЦИЯ СЛОВ: применяем фильтр в зависимости от параметра filter_type
    if filter_type == 'new':
        words = Word.objects.filter(knowledge_level=0)  # Только новые слова (уровень 0)
    elif filter_type == 'for_review':
        words = Word.objects.filter(knowledge_level__gte=1, knowledge_level__lte=4)  # Уровень 1-4
    elif filter_type == 'learned':
        words = Word.objects.filter(knowledge_level__gte=5)  # Изученные слова (уровень 5+)
    else: # 'all' или любой другой вариант
        words = Word.objects.all()  # Все слова

    # Передаем в шаблон все необходимые данные
    context = {
        'words': words,
        'is_reverse': is_reverse,
        'current_filter': filter_type,  # Передаем активный фильтр в шаблон
    }
    return render(request, 'app_vocab/word_list.html', context)
