import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand
from aiogram.types import BufferedInputFile
import random

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher()


# ===== СОСТОЯНИЯ FSM =====
class AddWord(StatesGroup):
    waiting_original = State()
    waiting_translation = State()


class QuizStates(StatesGroup):
    waiting_for_answer = State()


class CardStates(StatesGroup):
    viewing_card = State()
    rating_difficulty = State()


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
async def set_bot_commands():
    """Устанавливает меню команд в боте"""
    try:
        commands = [
            BotCommand(command="/start", description="Начать работу/Главное меню"),
            BotCommand(command="/words", description="Мои слова"),
            BotCommand(command="/add", description="Добавить слово"),
            BotCommand(command="/delete", description="Удалить слово"),
            BotCommand(command="/quiz", description="Пройти тест"),
            BotCommand(command="/cards", description="Карточки для повторения"),
            BotCommand(command="/stats", description="Статистика"),
            BotCommand(command="/audio", description="Озвучка слов"),
            BotCommand(command="/reminders", description="Управление напоминаниями"),
            BotCommand(command="/link", description="Привязать аккаунт"),
            BotCommand(command="/profile", description="Мой профиль"),
            #BotCommand(command="/menu", description="Главное меню"),
            BotCommand(command="/cancel", description="Отмена операции"),

        ]
        await bot.set_my_commands(commands)
        print("✅ Меню команд установлено")
    except Exception as e:
        print(f"⚠️ Не удалось установить меню команд: {e}")


def get_main_keyboard():
    """Возвращает основную клавиатуру"""
    keyboard = [
        [KeyboardButton(text="📚 Мои слова"), KeyboardButton(text="🧪 Тест")],
        [KeyboardButton(text="📖 Карточки"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="➕ Добавить слово"), KeyboardButton(text="🗑️Удалить слово")],
        [KeyboardButton(text="🔊 Озвучка"), KeyboardButton(text="🔔 Напомнить")],
        [KeyboardButton(text="🔗 Профиль"), KeyboardButton(text="⏹️ Отмена")]

    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def clear_previous_state(state: FSMContext):
    """Очищает предыдущее состояние FSM"""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        return True
    return False


async def show_next_card(message: types.Message, state: FSMContext, cards: list, current_index: int):
    """Показывает следующую карточку"""
    next_index = current_index + 1

    if next_index >= len(cards):
        await message.answer(
            "🎉 <b>Все карточки просмотрены!</b>\n\nОтличная работа! 🏆",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await state.clear()
        return

    card = cards[next_index]
    remaining = len(cards) - next_index - 1

    keyboard = [
        [KeyboardButton(text="🔄 Показать перевод")],
        [KeyboardButton(text="🔊 Озвучить слово")],
        [KeyboardButton(text="⏩ Следующая карточка")],
        [KeyboardButton(text="⏹️ Отмена")]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.answer(
        f"📖 <b>Карточка {next_index + 1}/{len(cards)}</b>\n\n"
        f"<i>{card['word']}</i>\n\n"
        f"Осталось карточек: {remaining}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    await state.update_data(
        current_index=next_index,
        translation=card['translation']
    )
    await state.set_state(CardStates.viewing_card)


# ===== ОСНОВНЫЕ КОМАНДЫ =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Начало работы с ботом"""
    await clear_previous_state(state)

    await message.answer(
        "👋 <b>Добро пожаловать в Vocabulary Trainer!</b>\n\n"
        "Я помогу вам изучать иностранные слова эффективно 🚀\n\n"
        "<b>Основные функции:</b>\n"
        "• 📚 <b>Мои слова</b> - просмотр вашего словаря\n"
        "• 🧪 <b>Тест</b> - проверка знаний с вариантами ответов\n"
        "• 📖 <b>Карточки</b> - повторение слов с интервалами\n"
        "• 📊 <b>Статистика</b> - прогресс изучения\n"
        "• 🔊 <b>Озвучка</b> - прослушивание произношения\n"
        "• 🗑️<b>Удаление слов</b> - управление вашим словарем\n\n"
        "Используйте кнопки ниже или команды из меню 📱",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Главное меню бота - перенаправляет на /start"""
    await clear_previous_state(state)
    await cmd_start(message, state)


@dp.message(Command("cancel"))
@dp.message(F.text.lower() == "отмена")
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отмена текущей операции"""
    if await clear_previous_state(state):
        await message.answer(
            "⏹️ <b>Операция отменена</b>\n\nВозвращаюсь в главное меню 🏠",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        await message.answer("❌ Нет активных операций для отмены")


# ===== РАБОТА СО СЛОВАМИ =====
@dp.message(Command("words"))
@dp.message(F.text == "📚 Мои слова")
async def cmd_words(message: types.Message, state: FSMContext):
    """Показывает все слова пользователя"""
    await clear_previous_state(state)

    from .models import Word
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_words_async():
        return list(Word.objects.all()[:10])

    words = await get_words_async()

    if words:
        response = "📚 <b>Ваши слова:</b>\n\n" + "\n".join(
            [f"• {word.original} - {word.translation}" for word in words]
        )
    else:
        response = "📝 У вас пока нет добавленных слов.\nИспользуйте /add чтобы добавить первое слово!"

    await message.answer(response, parse_mode='HTML')




@dp.message(Command("add"))
@dp.message(F.text == "➕ Добавить слово")
async def cmd_add(message: types.Message, state: FSMContext):
    """Начинает процесс добавления слова"""
    await clear_previous_state(state)
    await message.answer("📝 Введите иностранное слово:")
    await state.set_state(AddWord.waiting_original)


@dp.message(AddWord.waiting_original)
async def process_original(message: types.Message, state: FSMContext):
    """Обрабатывает ввод иностранного слова"""
    # ПРОВЕРЯЕМ ОТМЕНУ ПЕРЕД обработкой слова
    if message.text == "⏹️ Отмена":
        await cmd_cancel(message, state)
        return


    await state.update_data(original=message.text)
    await message.answer("📝 Теперь введите перевод:")
    await state.set_state(AddWord.waiting_translation)


@dp.message(AddWord.waiting_translation)
async def process_translation(message: types.Message, state: FSMContext):
    """Обрабатывает ввод перевода"""
    # ПРОВЕРЯЕМ ОТМЕНУ ПЕРЕД обработкой перевода
    if message.text == "⏹️ Отмена":
        await cmd_cancel(message, state)
        return

    user_data = await state.get_data()

    from .models import Word
    from asgiref.sync import sync_to_async

    @sync_to_async
    def save_word_async():
        # ПРОВЕРЯЕМ ДУБЛИКАТЫ
        if Word.objects.filter(original=user_data['original']).exists():
            return None, "duplicate"

        word = Word(
            original=user_data['original'],
            translation=message.text
        )
        word.save()
        return word, "success"

    word, result = await save_word_async()

    if result == "duplicate":
        await message.answer(
            f"❌ <b>Слово уже существует!</b>\n\n"
            f"Слово '<code>{user_data['original']}</code>' уже есть в вашем словаре.",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    elif word:
        await message.answer(
            f"✅ <b>Слово добавлено!</b>\n\n"
            f"<code>{word.original}</code> - <code>{word.translation}</code>",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )

    await state.clear()

# ===== УДАЛЕНИЕ СЛОВ =====
@dp.message(Command("delete"))
async def cmd_delete(message: types.Message, state: FSMContext):
    """Начинает процесс удаления слова"""
    await clear_previous_state(state)

    from .models import Word
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_words_async():
        return list(Word.objects.all()[:10])

    words = await get_words_async()

    if not words:
        await message.answer("📝 У вас пока нет добавленных слов.")
        return

    # Создаем клавиатуру со словами для удаления
    keyboard = []
    for word in words:
        keyboard.append([KeyboardButton(text=f"❌ {word.original} - {word.translation}")])

    # унифицируем с "⏹️ Отмена"
    keyboard.append([KeyboardButton(text="⏪ Отмена")])


    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.answer(
        "🗑️<b>Удаление слов</b>\n\n"
        "Выберите слово для удаления:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    await state.update_data(words_for_deletion=words)


@dp.message(F.text.startswith("❌"))
async def handle_word_deletion(message: types.Message, state: FSMContext):
    """Обрабатывает удаление выбранного слова"""
    from .models import Word
    from asgiref.sync import sync_to_async

    # Извлекаем оригинал слова из текста кнопки
    word_text = message.text.replace("❌ ", "").split(" - ")[0]

    @sync_to_async
    def delete_word_async():
        try:
            word = Word.objects.get(original=word_text)
            word.delete()
            return True, word_text
        except Word.DoesNotExist:
            return False, word_text

    success, deleted_word = await delete_word_async()

    if success:
        await message.answer(
            f"✅ <b>Слово удалено!</b>\n\n"
            f"Слово '<code>{deleted_word}</code>' удалено из вашего словаря.",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            f"❌ <b>Ошибка удаления</b>\n\n"
            f"Слово '<code>{deleted_word}</code>' не найдено.",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )

    await state.clear()


@dp.message(F.text == "⏪ Отмена")
async def handle_cancel_deletion(message: types.Message, state: FSMContext):
    """Отмена процесса удаления слов"""
    await state.clear()
    await message.answer(
        "⏹️ <b>Удаление отменено</b>\n\n"
        "Возвращаюсь в главное меню 🏠",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

@dp.message(F.text == "🗑️Удалить слово")
async def handle_delete_button(message: types.Message, state: FSMContext):
    """Обрабатывает кнопку удаления слова из основного меню"""
    await cmd_delete(message, state)


# ===== ТЕСТИРОВАНИЕ =====
@dp.message(Command("quiz"))
@dp.message(F.text == "🧪 Тест")
async def cmd_quiz(message: types.Message, state: FSMContext):
    """Запуск интерактивного теста"""
    await clear_previous_state(state)

    from .services import get_quiz_question_async

    question_data = await get_quiz_question_async()

    if not question_data:
        await message.answer(
            "❌ Недостаточно слов для теста. Добавьте слова через /add",
            reply_markup=get_main_keyboard()
        )
        return

    keyboard = []
    for option in question_data['options']:
        keyboard.append([KeyboardButton(text=option)])

        # КНОПКА ОТМЕНЫ
    keyboard.append([KeyboardButton(text="⏹️ Отмена")])

    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        f"🧪 <b>Тест:</b>\n\n<i>{question_data['question']}</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    await state.set_state(QuizStates.waiting_for_answer)
    await state.update_data(
        correct_answer=question_data['correct_answer'],
        question_type=question_data['type'],
        score=0,
        total_questions=1
    )


@dp.message(QuizStates.waiting_for_answer)
async def handle_quiz_answer(message: types.Message, state: FSMContext):
    """Обработка ответа в тесте"""
    # СНАЧАЛА ПРОВЕРЯЕМ ОТМЕНУ
    if message.text == "⏹️ Отмена":
        await cmd_cancel(message, state)
        return

    from .services import get_quiz_question_async

    user_data = await state.get_data()
    correct_answer = user_data.get('correct_answer')
    user_answer = message.text

    is_correct = user_answer == correct_answer
    current_score = user_data.get('score', 0)

    if is_correct:
        current_score += 1
        response = "✅ <b>Правильно!</b> 🎉"
    else:
        response = f"❌ <b>Неправильно</b>\nПравильный ответ: <code>{correct_answer}</code>"

    await state.update_data(score=current_score)
    next_question = await get_quiz_question_async()

    if next_question:
        keyboard = []
        for option in next_question['options']:
            keyboard.append([KeyboardButton(text=option)])

        # КНОПКА ОТМЕНЫ ДЛЯ СЛЕДУЮЩЕГО ВОПРОСА
        keyboard.append([KeyboardButton(text="⏹️ Отмена")])

        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            f"{response}\n\n🧪 <b>Следующий вопрос:</b>\n"
            f"<i>{next_question['question']}</i>\n\n"
            f"📊 Текущий счет: {current_score}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        await state.update_data(
            correct_answer=next_question['correct_answer'],
            question_type=next_question['type'],
            total_questions=user_data.get('total_questions', 0) + 1
        )

    else:
        total_questions = user_data.get('total_questions', 1)
        percentage = (current_score / total_questions) * 100

        await message.answer(
            f"🏁 <b>Тест завершен!</b>\n\n"
            f"📊 <b>Результат:</b>\n"
            f"• Правильных ответов: {current_score}/{total_questions}\n"
            f"• Успешность: {percentage:.1f}%\n\n"
            f"{'🎉 Отлично!' if percentage >= 80 else '👍 Хорошо!' if percentage >= 60 else '💪 Продолжайте практиковаться!'}",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await state.clear()


# ===== КАРТОЧКИ =====
@dp.message(Command("cards"))
@dp.message(F.text == "📖 Карточки")
async def cmd_cards(message: types.Message, state: FSMContext):
    """Показывает карточки для повторения"""
    await clear_previous_state(state)

    from .services import get_review_cards_async

    cards = await get_review_cards_async()

    if not cards:
        await message.answer(
            "❌ Нет слов для повторения. Добавьте слова через /add",
            reply_markup=get_main_keyboard()
        )
        return

    card = cards[0]
    remaining = len(cards) - 1

    # ОБНОВЛЕННАЯ КЛАВИАТУРА - добавил кнопку отмены
    keyboard = [
        [KeyboardButton(text="🔄 Показать перевод")],
        [KeyboardButton(text="🔊 Озвучить слово")],
        [KeyboardButton(text="⏩ Следующая карточка")],
        [KeyboardButton(text="⏹️ Отмена")]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.answer(
        f"📖 <b>Карточка 1/{len(cards)}</b>\n\n"
        f"<i>{card['word']}</i>\n\n"
        f"Осталось карточек: {remaining}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    await state.set_state(CardStates.viewing_card)
    await state.update_data(
        cards=cards,
        current_index=0,
        translation=card['translation']
    )


@dp.message(CardStates.viewing_card)
async def handle_card_action(message: types.Message, state: FSMContext):
    """Обрабатывает действия с карточками"""
    # СНАЧАЛА ПРОВЕРЯЕМ ОТМЕНУ
    if message.text == "⏹️ Отмена":
        await cmd_cancel(message, state)
        return


    user_data = await state.get_data()
    cards = user_data.get('cards', [])
    current_index = user_data.get('current_index', 0)
    translation = user_data.get('translation', '')
    current_card = cards[current_index] if current_index < len(cards) else None

    if not current_card:
        await message.answer("❌ Ошибка: карточка не найдена")
        await state.clear()
        return

    if message.text == "🔄 Показать перевод":
        keyboard = [
            [KeyboardButton(text="✅ Легко"), KeyboardButton(text="🔄 Нормально")],
            [KeyboardButton(text="❌ Трудно"), KeyboardButton(text="⏩ Следующая карточка")],
            [KeyboardButton(text="⏹️ Отмена")]
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )

        await message.answer(
            f"📖 <b>Перевод:</b>\n\n<code>{translation}</code>\n\n"
            f"<i>Оцените сложность слова:</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        await state.set_state(CardStates.rating_difficulty)

    elif message.text == "⏩ Следующая карточка":
        await show_next_card(message, state, cards, current_index)


    # ===== ОЗВУЧКА СЛОВА ТЕКУЩЕЙ КАРТОЧКИ =====

    elif message.text == "🔊 Озвучить слово":
        # Озвучка слова из текущей карточки
        import os
        from django.conf import settings

        # Используем слово из карточки, а не ищем в базе
        word_text = current_card['word']

        # Генерируем аудио через TTS сервис
        from .tts_service import text_to_speech
        from asgiref.sync import sync_to_async

        @sync_to_async
        def generate_audio_async():
            return text_to_speech(word_text, lang='en')

        tts_result = await generate_audio_async()

        if tts_result and 'url' in tts_result:
            audio_url = tts_result['url']
            filename = audio_url.replace('/media/audio/', '')
            filepath = os.path.join(settings.MEDIA_ROOT, 'audio', filename)

            if os.path.exists(filepath):
                with open(filepath, 'rb') as audio_file:
                    await message.answer(f"🔊 <b>{word_text}</b>", parse_mode='HTML')
                    await message.answer_audio(
                        audio=types.BufferedInputFile(audio_file.read(), filename=f"{word_text}.mp3"),
                        title=word_text,
                        performer="Vocabulary Trainer"
                    )
            else:
                await message.answer("❌ Аудиофайл не найден")
        else:
            await message.answer("❌ Не удалось озвучить слово")


@dp.message(CardStates.rating_difficulty)
async def handle_difficulty_rating(message: types.Message, state: FSMContext):
    """Обрабатывает оценку сложности слова"""
    user_data = await state.get_data()
    cards = user_data.get('cards', [])
    current_index = user_data.get('current_index', 0)

    difficulty_emojis = {
        "✅ Легко": "легко",
        "🔄 Нормально": "нормально",
        "❌ Трудно": "трудно"
    }

    if message.text in difficulty_emojis:
        difficulty = difficulty_emojis[message.text]
        current_card = cards[current_index]
        print(f"Пользователь оценил слово '{current_card['word']}' как '{difficulty}'")

        await message.answer(
            f"📊 Оценка сохранена: <b>{difficulty}</b>\n"
            f"Слово: <code>{current_card['word']}</code>",
            parse_mode='HTML'
        )

    await show_next_card(message, state, cards, current_index)


# ===== СТАТИСТИКА И ОЗВУЧКА =====

@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: types.Message, state: FSMContext):
    """Показывает статистику"""
    await clear_previous_state(state)

    from .models import Word
    from datetime import datetime, timedelta
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_stats_async():
        total_words = Word.objects.count()
        today = datetime.now().date()
        words_today = Word.objects.filter(date_added__date=today).count()

        # Статистика за последние 7 дней
        last_7_days = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = Word.objects.filter(date_added__date=date).count()
            last_7_days.append({'date': date, 'count': count})

        return total_words, words_today, last_7_days

    total_words, words_today, last_7_days = await get_stats_async()

    # Формируем расширенную статистику
    response = f"📊 <b>Ваша статистика:</b>\n\n"
    response += f"• 📚 Всего слов: <b>{total_words}</b>\n"
    response += f"• 🆕 Новые: <b>{words_today}</b>\n"
    response += f"• 📖 В процессе: <b>0</b>\n"  # Можно добавить логику прогресса
    response += f"• ✅ Изучено: <b>0</b>\n"  # Можно добавить логику изучения
    response += f"• 🎯 На сегодня: <b>{total_words}</b>\n\n"

    # Активность за неделю
    response += "<b>Активность за неделю:</b>\n"
    for day in last_7_days[:3]:  # Показываем последние 3 дня
        emoji = "🔥" if day['count'] > 0 else "⚪"
        response += f"{emoji} {day['date'].strftime('%d.%m')}: {day['count']} слов\n"

    response += "\n💪 Продолжайте в том же духе!"

    await message.answer(response, parse_mode='HTML')


# ===== ОЗВУЧКА say =====

@dp.message(Command("say"))
async def cmd_say(message: types.Message, state: FSMContext):
    """Озвучка конкретного слова"""
    await clear_previous_state(state)

    # Разбираем команду с любым количеством пробелов
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите слово для озвучки:\n\n"
            "<b>Примеры:</b>\n"
            "<code>/say hello</code>\n"
            "<code>/say   привет</code>\n"
            "<code>/saybreakfast</code>",
            parse_mode='HTML'
        )
        return

    word_text = ' '.join(parts[1:])  # Берем все после "/say"

    from .models import Word
    from asgiref.sync import sync_to_async

    @sync_to_async
    def find_word_async():
        try:
            # Ищем слово в базе
            return Word.objects.get(original=word_text)
        except Word.DoesNotExist:
            try:
                # Ищем по переводу
                return Word.objects.get(translation=word_text)
            except Word.DoesNotExist:
                return None

    word = await find_word_async()

    if word:
        audio_url = word.get_audio_url()

        if audio_url:
            # Открываем файл и отправляем как файл
            import os
            from django.conf import settings

            # Получаем полный путь к файлу
            filename = audio_url.replace('/media/audio/', '')
            filepath = os.path.join(settings.MEDIA_ROOT, 'audio', filename)

            if os.path.exists(filepath):
                # Отправляем файл напрямую
                with open(filepath, 'rb') as audio_file:
                    await message.answer(f"🔊 <b>{word.original}</b>", parse_mode='HTML')
                    await message.answer_audio(
                        audio=types.BufferedInputFile(audio_file.read(), filename=f"{word.original}.mp3"),
                        title=word.original,
                        performer="Vocabulary Trainer"
                    )
            else:
                await message.answer(f"❌ Аудиофайл для '{word.original}' не найден")
        else:
            await message.answer(f"❌ Не удалось сгенерировать аудио для '{word.original}'")
    else:
        await message.answer(f"❌ Слово '<code>{word_text}</code>' не найдено в вашем словаре", parse_mode='HTML')

# ===== ОЗВУЧКА audio =====

@dp.message(Command("audio"))
@dp.message(F.text == "🔊 Озвучка")
async def cmd_audio(message: types.Message, state: FSMContext):
    """Озвучка нескольких случайных слов"""
    await clear_previous_state(state)

    from .models import Word
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_words_async():
        return list(Word.objects.all()[:3])

    words = await get_words_async()

    if not words:
        await message.answer("❌ Нет слов для озвучки")
        return

    for word in words:
        audio_url = word.get_audio_url()

        if audio_url:
            import os
            from django.conf import settings

            filename = audio_url.replace('/media/audio/', '')
            filepath = os.path.join(settings.MEDIA_ROOT, 'audio', filename)

            if os.path.exists(filepath):
                with open(filepath, 'rb') as audio_file:
                    await message.answer(f"🔊 <b>{word.original}</b> - {word.translation}", parse_mode='HTML')
                    await message.answer_audio(
                        audio=types.BufferedInputFile(audio_file.read(), filename=f"{word.original}.mp3"),
                        title=word.original,
                        performer="Vocabulary Trainer"
                    )
            else:
                await message.answer(f"❌ Аудиофайл для '{word.original}' не найден")
        else:
            await message.answer(f"❌ Не удалось сгенерировать аудио для '{word.original}'")


# ===== НАПОМИНАНИЯ =====

@dp.message(Command("remind"))
async def cmd_remind(message: types.Message, state: FSMContext):
    """Ручной запуск напоминания о повторении слов"""
    await clear_previous_state(state)

    from .models import UserProfile, Word
    from asgiref.sync import sync_to_async
    import random

    @sync_to_async
    def get_reminder_data():
        try:
            profile = UserProfile.objects.get(telegram_id=message.from_user.id)
            # Берем 3 случайных слова для повторения
            words = list(Word.objects.all())
            if len(words) > 3:
                words = random.sample(words, 3)
            return profile, words
        except UserProfile.DoesNotExist:
            return None, []

    profile, words = await get_reminder_data()

    if not profile:
        await message.answer(
            "❌ <b>Сначала привяжите аккаунт</b>\n\n"
            "Используйте /link чтобы привязать Telegram к веб-профилю.",
            parse_mode='HTML'
        )
        return

    if not words:
        await message.answer(
            "📝 <b>Нет слов для повторения</b>\n\n"
            "Добавьте слова через /add чтобы получать напоминания.",
            parse_mode='HTML'
        )
        return

    # Формируем сообщение с словами для повторения
    words_list = "\n".join([f"• {word.original} - {word.translation}" for word in words])

    await message.answer(
        f"🔔 <b>Пора повторить слова!</b>\n\n"
        f"{words_list}\n\n"
        f"💡 <i>Используйте /quiz для теста или /cards для карточек</i>",
        parse_mode='HTML'
    )


@dp.message(F.text == "🔔 Напомнить")
async def handle_remind_button(message: types.Message, state: FSMContext):
    """Обрабатывает кнопку напоминаний из основного меню"""
    await cmd_reminders(message, state)



    from .models import UserProfile, Word
    from asgiref.sync import sync_to_async
    import random

    @sync_to_async
    def get_reminder_data():
        try:
            profile = UserProfile.objects.get(telegram_id=message.from_user.id)
            # Берем 3 случайных слова для повторения
            words = list(Word.objects.all())
            if len(words) > 3:
                words = random.sample(words, 3)
            return profile, words
        except UserProfile.DoesNotExist:
            return None, []

    profile, words = await get_reminder_data()

    if not profile:
        await message.answer(
            "❌ <b>Сначала привяжите аккаунт</b>\n\n"
            "Используйте /link чтобы привязать Telegram к веб-профилю.",
            parse_mode='HTML'
        )
        return

    if not words:
        await message.answer(
            "📝 <b>Нет слов для повторения</b>\n\n"
            "Добавьте слова через /add чтобы получать напоминания.",
            parse_mode='HTML'
        )
        return

    # Формируем сообщение со словами для повторения
    words_list = "\n".join([f"• {word.original} - {word.translation}" for word in words])

    await message.answer(
        f"🔔 <b>Пора повторить слова!</b>\n\n"
        f"{words_list}\n\n"
        f"💡 <i>Используйте /quiz для теста или /cards для карточек</i>",
        parse_mode='HTML'
    )

# ===== УПРАВЛЕНИЕ НАПОМИНАНИЯМИ =====

@dp.message(Command("reminders"))
async def cmd_reminders(message: types.Message, state: FSMContext):
    """Управление настройками напоминаний"""
    await clear_previous_state(state)

    from .models import UserProfile
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_profile_async():
        try:
            return UserProfile.objects.get(telegram_id=message.from_user.id)
        except UserProfile.DoesNotExist:
            return None

    profile = await get_profile_async()

    if not profile:
        await message.answer(
            "❌ <b>Сначала привяжите аккаунт</b>\n\n"
            "Используйте /link чтобы привязать Telegram к веб-профилю.",
            parse_mode='HTML'
        )
        return

    keyboard = [
        [KeyboardButton(text="🔄 Тестовое напоминание")],
        [KeyboardButton(text="⚙️ Настройки напоминаний")],
       #[KeyboardButton(text="📊 Статистика напоминаний")],
        [KeyboardButton(text="⏪ Назад в меню")]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.answer(
        f"🔔 <b>Управление напоминаниями</b>\n\n"
        f"Текущий лимит: <b>{profile.daily_review_limit}</b> слов/день\n"
        f"⏰ Периодичность: <b>ежедневно</b>\n"
        f"Статус: <b>Активный</b>\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@dp.message(F.text == "🔄 Тестовое напоминание")
async def handle_test_reminder(message: types.Message, state: FSMContext):
    """Отправляет тестовое напоминание"""
    await cmd_remind(message, state)

@dp.message(F.text == "⏪ Назад в меню")
async def handle_back_to_menu(message: types.Message, state: FSMContext):
    """Возвращает в главное меню"""
    await cmd_start(message, state)


# ===== НАСТРОЙКИ НАПОМИНАНИЙ =====

@dp.message(F.text == "⚙️ Настройки напоминаний")
async def handle_reminder_settings(message: types.Message, state: FSMContext):
    """Настройка параметров напоминаний"""
    from .models import UserProfile
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_profile_async():
        try:
            return UserProfile.objects.get(telegram_id=message.from_user.id)
        except UserProfile.DoesNotExist:
            return None

    profile = await get_profile_async()

    if not profile:
        await message.answer("❌ Сначала привяжите аккаунт через /link")
        return

    keyboard = [
        [KeyboardButton(text="5 слов/день"), KeyboardButton(text="10 слов/день")],
        [KeyboardButton(text="15 слов/день"), KeyboardButton(text="20 слов/день")],
        [KeyboardButton(text="⏪ Назад к напоминаниям")]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.answer(
        f"⚙️ <b>Настройки напоминаний</b>\n\n"
        f"Текущий лимит: <b>{profile.daily_review_limit}</b> слов/день\n\n"
        f"Выберите новый лимит:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ===== ДНЕВНОЙ ЛИМИТ =====

@dp.message(F.text.contains("слов/день"))
async def handle_limit_change(message: types.Message):
    """Обрабатывает изменение лимита слов"""
    from .models import UserProfile
    from asgiref.sync import sync_to_async

    # Извлекаем число из текста (например: "10 слов/день" -> 10)
    new_limit = int(message.text.split()[0])

    @sync_to_async
    def update_limit_async():
        try:
            profile = UserProfile.objects.get(telegram_id=message.from_user.id)
            profile.daily_review_limit = new_limit
            profile.save()
            return True
        except UserProfile.DoesNotExist:
            return False

    success = await update_limit_async()

    if success:
        await message.answer(
            f"✅ <b>Лимит обновлен!</b>\n\n"
            f"Теперь вы будете получать <b>{new_limit}</b> слов для повторения.",
            parse_mode='HTML'
        )
        await cmd_reminders(message, None)  # Возвращаем в меню напоминаний
    else:
        await message.answer("❌ Ошибка обновления лимита")



@dp.message(F.text == "⏪ Назад к напоминаниям")
async def handle_back_to_reminders(message: types.Message, state: FSMContext):
    """Возвращает в меню управления напоминаниями"""
    await cmd_reminders(message, state)





# ===== ПРИВЯЗКА Telegram-аккаунтов к веб-пользователям =====

@dp.message(Command("link"))
@dp.message(F.text == "🔗 Привязать аккаунт")
async def cmd_link(message: types.Message, state: FSMContext):
    """Привязка Telegram аккаунта к веб-пользователю"""
    await clear_previous_state(state)

    from django.contrib.auth.models import User
    from .models import UserProfile
    from asgiref.sync import sync_to_async
    from django.db import IntegrityError

    @sync_to_async
    def link_account_async():
        try:
            # Пытаемся найти существующий профиль по telegram_id
            try:
                profile = UserProfile.objects.get(telegram_id=message.from_user.id)
                # Профиль уже существует - обновляем username
                profile.telegram_username = message.from_user.username
                profile.save()
                return False, profile  # created = False
            except UserProfile.DoesNotExist:
                # Создаем новый профиль
                # Берем первого пользователя или создаем нового
                user = User.objects.first()
                if not user:
                    user = User.objects.create_user('telegram_user', '', 'password')

                profile = UserProfile.objects.create(
                    user=user,
                    telegram_id=message.from_user.id,
                    telegram_username=message.from_user.username
                )
                return True, profile  # created = True

        except IntegrityError:
            # Если возникла ошибка уникальности, находим и обновляем существующий профиль
            profile = UserProfile.objects.get(user=User.objects.first())
            profile.telegram_id = message.from_user.id
            profile.telegram_username = message.from_user.username
            profile.save()
            return False, profile

    created, profile = await link_account_async()

    if created:
        response = (
            "✅ <b>Аккаунт привязан!</b>\n\n"
            f"Ваш Telegram аккаунт @{message.from_user.username} "
            f"успешно привязан к веб-профилю."
        )
    else:
        response = (
            "🔗 <b>Аккаунт обновлен</b>\n\n"
            f"Данные вашего Telegram аккаунта обновлены: @{message.from_user.username}"
        )

    await message.answer(response, parse_mode='HTML')


@dp.message(Command("profile"))
async def cmd_profile(message: types.Message, state: FSMContext):
    """Показывает информацию о привязанном профиле"""
    await clear_previous_state(state)

    from .models import UserProfile
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_profile_async():
        try:
            return UserProfile.objects.get(telegram_id=message.from_user.id)
        except UserProfile.DoesNotExist:
            return None

    profile = await get_profile_async()

    if profile:
        # Получаем данные пользователя через асинхронную обертку
        @sync_to_async
        def get_user_data():
            return {
                'username': profile.user.username,
                'telegram_id': profile.telegram_id,
                'telegram_username': profile.telegram_username,
                'daily_review_limit': profile.daily_review_limit
            }

        user_data = await get_user_data()

        response = (
            "👤 <b>Ваш профиль</b>\n\n"
            f"• Веб-пользователь: <code>{user_data['username']}</code>\n"
            f"• Telegram ID: <code>{user_data['telegram_id']}</code>\n"
            f"• Username: @{user_data['telegram_username'] or 'не указан'}\n"
            f"• Лимит повторений: <b>{user_data['daily_review_limit']}</b> слов/день\n\n"
            f"Аккаунт успешно привязан! 🎯"
        )
    else:
        response = (
            "❌ <b>Профиль не привязан</b>\n\n"
            "Используйте команду /link чтобы привязать "
            "ваш Telegram аккаунт к веб-профилю."
        )

    await message.answer(response, parse_mode='HTML')


# обработчик для кнопки "🔗 Профиль"
@dp.message(F.text == "🔗 Профиль")
async def handle_profile_button(message: types.Message, state: FSMContext):
    """Обрабатывает кнопку профиля из основного меню"""
    await cmd_profile(message, state)



# временная команда для очистки базы от дублей ошибочных слов
@dp.message(Command("cleanup"))
async def cmd_cleanup(message: types.Message):
    """Очистка базы от ошибочных слов (временная команда)"""
    from .models import Word
    from asgiref.sync import sync_to_async

    @sync_to_async
    def cleanup_words():
        # Удаляем слова, которые являются командами
        words_to_delete = Word.objects.filter(original__in=["steamship", "/cancel"])
        count = words_to_delete.count()
        words_to_delete.delete()
        return count

    deleted_count = await cleanup_words()

    await message.answer(
        f"🧹 <b>Очистка завершена!</b>\n\n"
        f"Удалено ошибочных слов: {deleted_count}",
        parse_mode='HTML'
    )


# ===== ЗАПУСК БОТА =====
async def main():
    await set_bot_commands()
    print("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())