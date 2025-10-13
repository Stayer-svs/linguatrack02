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
            BotCommand(command="/start", description="Начать работу"),
            BotCommand(command="/words", description="Мои слова"),
            BotCommand(command="/add", description="Добавить слово"),
            BotCommand(command="/quiz", description="Пройти тест"),
            BotCommand(command="/cards", description="Карточки для повторения"),
            BotCommand(command="/stats", description="Статистика"),
            BotCommand(command="/audio", description="Озвучка слов"),
            BotCommand(command="/menu", description="Главное меню"),
            BotCommand(command="/cancel", description="Отмена операции")
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
        [KeyboardButton(text="➕ Добавить слово"), KeyboardButton(text="🔊 Озвучка")],
        [KeyboardButton(text="⏹️ Отмена")]
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
        [KeyboardButton(text="⏩ Следующая карточка")]
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
        "• 🔊 <b>Озвучка</b> - прослушивание произношения\n\n"
        "Используйте кнопки ниже или команды из меню 📱",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Главное меню бота"""
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
    await state.update_data(original=message.text)
    await message.answer("📝 Теперь введите перевод:")
    await state.set_state(AddWord.waiting_translation)


@dp.message(AddWord.waiting_translation)
async def process_translation(message: types.Message, state: FSMContext):
    """Обрабатывает ввод перевода и сохраняет слово"""
    user_data = await state.get_data()

    from .models import Word
    from asgiref.sync import sync_to_async

    @sync_to_async
    def save_word_async():
        word = Word(
            original=user_data['original'],
            translation=message.text
        )
        word.save()
        return word

    word = await save_word_async()

    await message.answer(
        f"✅ <b>Слово добавлено!</b>\n\n"
        f"<code>{word.original}</code> - <code>{word.translation}</code>",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )
    await state.clear()


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

    keyboard = [
        [KeyboardButton(text="🔄 Показать перевод")],
        [KeyboardButton(text="⏩ Следующая карточка")]
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
    user_data = await state.get_data()
    cards = user_data.get('cards', [])
    current_index = user_data.get('current_index', 0)
    translation = user_data.get('translation', '')

    if message.text == "🔄 Показать перевод":
        keyboard = [
            [KeyboardButton(text="✅ Легко"), KeyboardButton(text="🔄 Нормально"), KeyboardButton(text="❌ Трудно")],
            [KeyboardButton(text="⏩ Следующая карточка")]
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )

        await message.answer(
            f"📖 <b>Перевод:</b>\n\n<code>{translation}</code>\n\n<i>Оцените сложность слова:</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        await state.set_state(CardStates.rating_difficulty)

    elif message.text == "⏩ Следующая карточка":
        await show_next_card(message, state, cards, current_index)


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


# ===== ЗАПУСК БОТА =====
async def main():
    await set_bot_commands()
    print("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())