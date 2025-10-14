# app_vocab/reminder_service.py
import asyncio
from asgiref.sync import sync_to_async
from .models import UserProfile, Word
import random


@sync_to_async
def get_users_for_reminders():
    """Возвращает пользователей с привязанными Telegram аккаунтами"""
    return list(UserProfile.objects.filter(telegram_id__isnull=False))


@sync_to_async
def get_random_words(count=3):
    """Возвращает случайные слова для напоминания"""
    words = list(Word.objects.all())
    if len(words) > count:
        return random.sample(words, count)
    return words


async def send_reminder_to_user(bot, user_profile):
    """Отправляет напоминание конкретному пользователю"""
    try:
        words = await get_random_words(3)

        if not words:
            return False

        words_list = "\n".join([f"• {word.original} - {word.translation}" for word in words])

        await bot.send_message(
            chat_id=user_profile.telegram_id,
            text=f"🔔 <b>Пора повторить слова!</b>\n\n"
                 f"{words_list}\n\n"
                 f"💡 <i>Используйте /quiz для теста или /cards для карточек</i>",
            parse_mode='HTML'
        )
        return True
    except Exception as e:
        print(f"Ошибка отправки напоминания пользователю {user_profile.telegram_id}: {e}")
        return False


async def send_daily_reminders(bot):
    """Отправляет ежедневные напоминания всем пользователям"""
    users = await get_users_for_reminders()

    if not users:
        print("Нет пользователей для напоминаний")
        return

    success_count = 0
    for user in users:
        if await send_reminder_to_user(bot, user):
            success_count += 1
        await asyncio.sleep(1)  # Пауза между отправками

    print(f"📨 Отправлено напоминаний: {success_count}/{len(users)}")
