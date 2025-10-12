# app_vocab/bot.py

import os
import random
import django
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async  # для Django запросов в контексте aiogram
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext



# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from .models import Word

bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher()

# Храним режим реверса для каждого пользователя (в памяти)
user_reverse_mode = {}

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="📚 Слова на сегодня")
            ],
            [
                KeyboardButton(text="🎯 Тест"),
                KeyboardButton(text="🃏 Карточки")
            ],
            [
                KeyboardButton(text="🔊 Озвучить слово"),
                KeyboardButton(text="🔗 Привязать аккаунт")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


# Асинхронные обертки для синхронных методов Django ORM
@sync_to_async
def get_all_words():
    """Асинхронно получает все слова из базы"""
    return list(Word.objects.all())


@sync_to_async
def get_word_by_id(word_id):
    """Асинхронно получает слово по ID"""
    try:
        return Word.objects.get(id=word_id)
    except Word.DoesNotExist:
        return None


@sync_to_async
def update_word_knowledge(word, increment=True):
    """Асинхронно обновляет уровень знания слова"""
    if increment:
        word.knowledge_level += 1
    else:
        if word.knowledge_level > 0:
            word.knowledge_level -= 1
    word.save()
    return word.knowledge_level


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "Привет! 👋\n"
        "Я бот для изучения иностранных слов.\n\n"
        "Используй кнопки ниже для управления тренировкой."
    )
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎓 Начать тренировку")],
            [KeyboardButton(text="🔄 Режим: Слово → Перевод"), KeyboardButton(text="📊 Статистика")]
        ],
        resize_keyboard=True
    )
    #await message.answer(welcome_text, reply_markup=keyboard)
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


# Обработчик кнопки смены режима
@dp.message(F.text.startswith("🔄 Режим:"))
async def toggle_reverse_mode(message: types.Message):
    user_id = message.from_user.id
    current_mode = user_reverse_mode.get(user_id, False)

    new_mode = not current_mode
    user_reverse_mode[user_id] = new_mode

    if new_mode:
        mode_text = "ПЕРЕВОД → СЛОВО"
        hint = "(Показывается перевод, нужно вспомнить слово)"
    else:
        mode_text = "СЛОВО → ПЕРЕВОД"
        hint = "(Показывается слово, нужно вспомнить перевод)"

    await message.answer(f"Режим изменен на: {mode_text}\n{hint}")


# Обработчик кнопки "Начать тренировку"
@dp.message(F.text == "🎓 Начать тренировку")
async def start_training(message: types.Message):
    await send_random_word(message.from_user.id)


# Функция для отправки случайного слова пользователю
async def send_random_word(user_id: int):
    # Используем асинхронную обертку для получения слов
    all_words = await get_all_words()

    if not all_words:
        await bot.send_message(user_id, "В вашем словаре пока нет слов. Добавьте их через веб-интерфейс.")
        return

    word = random.choice(all_words)
    is_reverse = user_reverse_mode.get(user_id, False)

    if is_reverse:
        question = f"<b>Какой перевод у слова?</b>\n\n{word.translation}"
    else:
        question = f"<b>Как переводится слово?</b>\n\n{word.original}"
        if word.transcription:
            question += f"\n<code>[{word.transcription}]</code>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤔 Показать ответ", callback_data=f"show_{word.id}")],
    ])

    await bot.send_message(user_id, question, reply_markup=keyboard, parse_mode='HTML')


# Обработчик нажатия на инлайн-кнопку "Показать ответ"
@dp.callback_query(F.data.startswith("show_"))
async def show_answer(callback: types.CallbackQuery):
    word_id = int(callback.data.split('_')[1])

    # Используем асинхронную обертку для поиска слова
    word = await get_word_by_id(word_id)

    if not word:
        await callback.answer("Слово не найдено!")
        return

    user_id = callback.from_user.id
    is_reverse = user_reverse_mode.get(user_id, False)

    if is_reverse:
        answer = f"<b>Правильный ответ:</b>\n{word.original}"
        if word.transcription:
            answer += f"\n<code>[{word.transcription}]</code>"
    else:
        answer = f"<b>Правильный ответ:</b>\n{word.translation}"

    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Знаю", callback_data=f"know_{word.id}"),
         InlineKeyboardButton(text="❌ Не знаю", callback_data=f"dont_know_{word.id}")],
        [InlineKeyboardButton(text="➡️ Следующее слово", callback_data="next_word")]
    ])

    await callback.message.edit_text(
        f"{callback.message.text}\n\n{answer}",
        reply_markup=new_keyboard,
        parse_mode='HTML'
    )
    await callback.answer()


# Обработчики кнопок "Знаю" и "Не знаю"
@dp.callback_query(F.data.startswith("know_"))
async def know_word(callback: types.CallbackQuery):
    word_id = int(callback.data.split('_')[1])

    word = await get_word_by_id(word_id)
    if word:
        new_level = await update_word_knowledge(word, increment=True)
        await callback.answer(f"Отлично! Уровень слова увеличен до {new_level}")
    else:
        await callback.answer("Ошибка: слово не найдено!")


@dp.callback_query(F.data.startswith("dont_know_"))
async def dont_know_word(callback: types.CallbackQuery):
    word_id = int(callback.data.split('_')[1])

    word = await get_word_by_id(word_id)
    if word:
        new_level = await update_word_knowledge(word, increment=False)
        await callback.answer(f"Повторим! Уровень слова: {new_level}")
    else:
        await callback.answer("Ошибка: слово не найдено!")


# Обработчик кнопки "Следующее слово"
@dp.callback_query(F.data == "next_word")
async def next_word(callback: types.CallbackQuery):
    await callback.message.delete()
    await send_random_word(callback.from_user.id)
    await callback.answer()


# СТАРЫЙ СИНТАКСИС (aiogram 2.x):
# @dp.message_handler(commands=['link'])

# НОВЫЙ СИНТАКСИС (aiogram 3.x):
@dp.message(Command("link"))
async def link_account(message: Message):
    """Генерация кода для привязки аккаунта"""
    user_id = message.from_user.id

    # Генерируем уникальный код
    import secrets
    link_code = secrets.token_hex(4).upper()  # 8-символьный код

    await message.answer(
        f"🔗 **Привязка аккаунта**\n\n"
        f"Ваш код: `{link_code}`\n\n"
        f"1. Перейдите в веб-версию\n"
        f"2. Введите этот код в разделе Telegram-бота\n"
        f"3. Аккаунты будут связаны автоматически\n\n"
        f"Код действителен 10 минут ⏳"
    )

@dp.message(Command("say"))
async def say_word(message: Message):
    """Озвучка слова через TTS"""
    command_parts = message.text.split(' ', 1)

    if len(command_parts) < 2:
        await message.answer(
            "🎯 **Использование:**\n"
            "`/say слово` - озвучить слово\n\n"
            "**Пример:**\n"
            "`/say hello`\n"
            "`/say computer`"
        )
        return

    word_to_speak = command_parts[1].strip()

    if len(word_to_speak) > 50:
        await message.answer("❌ Слишком длинный текст (максимум 50 символов)")
        return

    processing_msg = await message.answer("🔊 Генерирую аудио...")

    try:
        from app_vocab.tts_service import text_to_speech

        result = text_to_speech(word_to_speak, lang='en')

        if result and result['filepath']:
            # ПРАВИЛЬНЫЙ СПОСОБ В aiogram 3.x
            with open(result['filepath'], 'rb') as audio_file:
                audio_data = audio_file.read()

            voice_message = BufferedInputFile(audio_data, filename="word.mp3")

            await message.answer_voice(
                voice=voice_message,
                caption=f"🔊 **{word_to_speak}**"
            )
            await processing_msg.delete()
        else:
            await processing_msg.edit_text("❌ Ошибка генерации аудио")

    except Exception as e:
        await processing_msg.edit_text(f"❌ Ошибка: {str(e)}")
        print(f"TTS Error in bot: {e}")


@dp.message(F.text == "📊 Статистика")
async def show_progress(message: Message):
    """Показать реальную статистику обучения"""
    try:
        from app_vocab.services import get_user_statistics
        from django.contrib.auth.models import User

        demo_user = await sync_to_async(User.objects.first)()

        if demo_user:
            stats = await sync_to_async(get_user_statistics)(demo_user)

            stats_text = (
                "📊 **Ваша статистика:**\n\n"
                f"• 📚 Всего слов: {stats['total_words']}\n"
                f"• 🆕 Новые: {stats['new_words']}\n"
                f"• 📖 В процессе: {stats['learning_words']}\n"
                f"• ✅ Изучено: {stats['learned_words']}\n"
                f"• 🎯 На сегодня: {stats['today_words']}\n\n"
                "💪 Продолжайте в том же духе!"
            )
        else:
            stats_text = "❌ Нет данных для статистики"

    except Exception as e:
        print(f"Stats error: {e}")
        stats_text = f"❌ Ошибка загрузки статистики: {str(e)}"

    await message.answer(stats_text)


@dp.message(F.text == "📚 Слова на сегодня")
async def today_words(message: Message):
    """Показать реальные слова для повторения сегодня"""
    try:
        from app_vocab.services import get_today_words
        from django.contrib.auth.models import User

        demo_user = await sync_to_async(User.objects.first)()

        if demo_user:
            # Получаем QuerySet и оцениваем его
            today_words_qs = await sync_to_async(get_today_words)(demo_user, limit=10)
            today_words_list = await sync_to_async(list)(today_words_qs)

            if today_words_list:
                words_text = "📚 **Слова на сегодня:**\n\n"
                for user_word in today_words_list:
                    words_text += f"• {user_word.word.original} - {user_word.word.translation}\n"

                words_text += f"\n🎯 Всего для повторения: {len(today_words_list)} слов"
            else:
                words_text = "🎉 **Отличная работа!**\n\nНа сегодня слов для повторения нет."

        else:
            words_text = "❌ Нет данных о словах"

    except Exception as e:
        print(f"Today words error: {e}")
        words_text = "❌ Ошибка загрузки слов"

    await message.answer(words_text, reply_markup=get_main_keyboard())


@dp.message(F.text == "🎯 Тест")
async def start_test(message: Message):
    """Начать тест"""
    await message.answer(
        "🧪 **Режим теста**\n\n"
        "Скоро здесь будет интерактивный тест!\n\n"
        "А пока используйте тренировку:",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🃏 Карточки")
async def show_cards(message: Message):
    """Показать все карточки"""
    await message.answer(
        "🃏 **Все карточки**\n\n"
        "Скоро здесь будет список всех ваших слов!",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🔗 Привязать аккаунт")
async def link_account_button(message: Message):
    """Привязать аккаунт через кнопку"""
    await message.answer(
        "🔗 **Привязка аккаунта**\n\n"
        "Используйте команду:\n"
        "`/link` - получить код привязки\n\n"
        "Затем введите код в веб-версии.",
        reply_markup=get_main_keyboard()
    )


# Добавляем состояния для теста
class QuizStates(StatesGroup):
    waiting_for_answer = State()
    in_progress = State()


# Добавляем команду /quiz
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message, state: FSMContext):
    """Запуск интерактивного теста"""
    #from .services import get_quiz_question
    from .services import get_quiz_question_async

    #question_data = get_quiz_question()
    question_data = await get_quiz_question_async()

    if not question_data:
        await message.answer(
            "❌ Недостаточно слов для теста. Добавьте слова через /add",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    # Создаем клавиатуру с вариантами ответов
    keyboard = []
    for option in question_data['options']:
        keyboard.append([types.KeyboardButton(text=option)])

    reply_markup = types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    # Отправляем вопрос
    await message.answer(
        f"🧪 <b>Тест:</b>\n\n"
        f"<i>{question_data['question']}</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    # Сохраняем данные вопроса в состоянии
    await state.set_state(QuizStates.waiting_for_answer)
    await state.update_data(
        correct_answer=question_data['correct_answer'],
        question_type=question_data['type'],
        score=0,
        total_questions=1
    )


# Добавляем обработчик ответов
@dp.message(QuizStates.waiting_for_answer)
async def handle_quiz_answer(message: types.Message, state: FSMContext):
    """Обработка ответа в тесте"""
    #from .services import get_quiz_question
    from .services import get_quiz_question_async

    user_data = await state.get_data()
    correct_answer = user_data.get('correct_answer')
    user_answer = message.text

    # Проверяем ответ
    is_correct = user_answer == correct_answer
    current_score = user_data.get('score', 0)

    if is_correct:
        current_score += 1
        response = "✅ <b>Правильно!</b> 🎉"
    else:
        response = f"❌ <b>Неправильно</b>\nПравильный ответ: <code>{correct_answer}</code>"

    # Обновляем счет
    await state.update_data(score=current_score)

    # Получаем следующий вопрос
    #next_question = get_quiz_question()
    next_question = await get_quiz_question_async()

    if next_question:
        # Создаем клавиатуру для следующего вопроса
        keyboard = []
        for option in next_question['options']:
            keyboard.append([types.KeyboardButton(text=option)])

        reply_markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        # Отправляем результат и следующий вопрос
        await message.answer(
            f"{response}\n\n"
            f"🧪 <b>Следующий вопрос:</b>\n"
            f"<i>{next_question['question']}</i>\n\n"
            f"📊 Текущий счет: {current_score}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        # Обновляем состояние
        await state.update_data(
            correct_answer=next_question['correct_answer'],
            question_type=next_question['type'],
            total_questions=user_data.get('total_questions', 0) + 1
        )

    else:
        # Завершаем тест
        total_questions = user_data.get('total_questions', 1)
        percentage = (current_score / total_questions) * 100

        await message.answer(
            f"🏁 <b>Тест завершен!</b>\n\n"
            f"📊 <b>Результат:</b>\n"
            f"• Правильных ответов: {current_score}/{total_questions}\n"
            f"• Успешность: {percentage:.1f}%\n\n"
            f"{'🎉 Отлично!' if percentage >= 80 else '👍 Хорошо!' if percentage >= 60 else '💪 Продолжайте практиковаться!'}",
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        await state.clear()


# Запуск бота
async def main():
    print("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())