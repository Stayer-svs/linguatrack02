# app_vocab/bot.py

import os
import random
import django
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async  # ИМПОРТИРУЕМ ВАЖНУЮ ФУНКЦИЮ!

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from .models import Word

bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher()

# Храним режим реверса для каждого пользователя (в памяти)
user_reverse_mode = {}


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
    await message.answer(welcome_text, reply_markup=keyboard)


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


# Запуск бота
async def main():
    print("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())