# Скрипт для запуска Telegram-бота

import asyncio
import os
import django

# Важно: указываем путь к настройкам Django перед импортом моделей
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Импорт и запуск бота делается ПОСЛЕ настройки Django
from app_vocab.bot import main

if __name__ == '__main__':
    print("Бот запускается...")
    asyncio.run(main())