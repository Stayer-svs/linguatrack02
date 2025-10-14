# Скрипт для запуска Telegram-бота

import asyncio
import os
import django

# Важно: указываем путь к настройкам Django перед импортом моделей
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Импорт и запуск бота делается ПОСЛЕ настройки Django
from app_vocab.bot import main, bot


async def schedule_reminders():
    """Планировщик ежедневных напоминаний"""
    while True:
        # Ждем 60 секунд для тестирования
      # await asyncio.sleep(60)
        # Ждем 24 часа (86400 секунд) между напоминаниями
        await asyncio.sleep(86400)


        try:
            from app_vocab.reminder_service import send_daily_reminders
            await send_daily_reminders(bot)
          # print("✅ Напоминания отправлены")
            print("✅ Ежедневные напоминания отправлены")
        except Exception as e:
            print(f"❌ Ошибка в планировщике напоминаний: {e}")


async def run_bot_with_reminders():
    """Запускает бота вместе с системой напоминаний"""
    # Запуск планировщика напоминаний в фоне
    asyncio.create_task(schedule_reminders())

    # Запуск основного бота
    await main()


if __name__ == '__main__':
    print("Бот запускается...")
    asyncio.run(run_bot_with_reminders())