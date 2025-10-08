from gtts import gTTS
import os
from django.conf import settings
import uuid


def text_to_speech(text, lang='en'):
    """
    Преобразование текста в речь через gTTS
    Возвращает URL к аудиофайлу
    """
    try:
        # Создаем папку для аудиофайлов если нет
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        os.makedirs(audio_dir, exist_ok=True)

        # Генерируем уникальное имя файла
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(audio_dir, filename)

        # Создаем TTS и сохраняем файл
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(filepath)

        return f"/media/audio/{filename}"

    except Exception as e:
        print(f"TTS Error: {e}")
        return None